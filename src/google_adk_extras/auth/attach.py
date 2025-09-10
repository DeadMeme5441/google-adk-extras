from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
import base64
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from .config import AuthConfig, JwtIssuerConfig, JwtValidatorConfig
from .jwt_utils import decode_jwt, encode_jwt, now_ts
from typing import Any


def attach_auth(app: FastAPI, cfg: Optional[AuthConfig]) -> None:
    """Attach optional auth to the provided FastAPI app.

    - Adds middleware that enforces auth on sensitive routes.
    - Optionally registers token issuance endpoints if configured.
    """
    if not cfg or not cfg.enabled or cfg.allow_no_auth:
        return

    validator = cfg.jwt_validator
    issuer_cfg = cfg.jwt_issuer
    api_keys = set(cfg.api_keys or [])
    basic_users = cfg.basic_users or {}
    auth_store: Optional[Any] = None
    if issuer_cfg and issuer_cfg.database_url:
        try:
            from .sql_store import AuthStore  # type: ignore
            auth_store = AuthStore(issuer_cfg.database_url)
        except Exception:
            # SQL store not available; API key issuance and password grants will be unavailable.
            auth_store = None

    # Decide gating for each method (None => auto)
    allow_api_key = (
        cfg.allow_api_key if cfg.allow_api_key is not None else (bool(api_keys) or bool(issuer_cfg and issuer_cfg.database_url))
    )
    allow_basic = (
        cfg.allow_basic if cfg.allow_basic is not None else (bool(basic_users) or bool(issuer_cfg and issuer_cfg.database_url))
    )
    allow_bearer_jwt = (
        cfg.allow_bearer_jwt if cfg.allow_bearer_jwt is not None else (validator is not None)
    )
    allow_issuer_endpoints = (
        cfg.allow_issuer_endpoints if cfg.allow_issuer_endpoints is not None else bool(issuer_cfg and issuer_cfg.enabled)
    )

    # Security helpers
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def _authenticate(request: Request) -> dict:
        # API Key
        if allow_api_key:
            api_key = None
            if cfg.allow_query_api_key:
                api_key = request.query_params.get("api_key")
            if not api_key:
                api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
            if not api_key:
                api_key = await api_key_header.__call__(request)
            if api_key and api_key in api_keys:
                return {"method": "api_key", "sub": "api_key_client"}
            if api_key and auth_store and auth_store.verify_api_key(api_key):
                return {"method": "api_key", "sub": "api_key_client"}

        # Basic
        authz = request.headers.get("authorization") or request.headers.get("Authorization")
        if allow_basic and authz and authz.lower().startswith("basic "):
            try:
                b64 = authz.split(" ", 1)[1]
                raw = base64.b64decode(b64).decode("utf-8")
                username, _, password = raw.partition(":")
            except Exception:
                username, password = "", ""
            # If SQL store present, try it first; else fall back to configured map
            if auth_store:
                uid = auth_store.authenticate_basic(username, password)
                if uid:
                    return {"method": "basic", "sub": uid, "username": username}
            stored = basic_users.get(username)
            if stored and (stored == password):
                return {"method": "basic", "sub": username, "username": username}

        # Bearer JWT
        if allow_bearer_jwt and authz and authz.lower().startswith("bearer "):
            token = authz.split(" ", 1)[1]
            if validator and (validator.jwks_url or validator.hs256_secret):
                try:
                    claims = decode_jwt(
                        token,
                        issuer=validator.issuer,
                        audience=validator.audience,
                        jwks_url=validator.jwks_url,
                        hs256_secret=validator.hs256_secret,
                    )
                    sub = str(claims.get("sub"))
                    if not sub:
                        raise HTTPException(status_code=401, detail="Invalid token: no subject")
                    return {"method": "jwt", "sub": sub, "claims": claims}
                except Exception as e:
                    raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

        raise HTTPException(status_code=401, detail="Unauthorized")

    def _path_requires_auth(path: str, method: str) -> bool:
        method = method.upper()
        # Always protect core run endpoints
        if path == "/run" and method == "POST":
            return True
        if path == "/run_sse" and method == "POST":
            return True
        # Protect streaming controller HTTP endpoints (SSE + HTTP send)
        if path.startswith("/stream/"):
            return True
        # Sessions and artifacts under /apps
        if path.startswith("/apps/"):
            # Allow metrics to be toggled
            if path.endswith("/metrics-info") and method == "GET":
                return cfg.protect_metrics
            return True
        # Debug and builder are privileged
        if path.startswith("/debug/") or path.startswith("/builder/"):
            return True
        # API key management endpoints
        if path.startswith("/auth/api-keys"):
            return True
        # Optionally protect list-apps
        if path == "/list-apps" and method == "GET":
            return cfg.protect_list_apps
        return False

    class _AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            if not _path_requires_auth(path, request.method):
                return await call_next(request)
            # Authenticate
            try:
                request.state.identity = await _authenticate(request)
            except HTTPException as e:
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": e.detail}, status_code=e.status_code)
            # Optional: Enforce user ownership when path has /users/{user_id}/
            try:
                parts = path.strip("/").split("/")
                # For SSE: enforce that ?userId matches token subject when present
                if path.startswith("/stream/"):
                    q_uid = request.query_params.get("userId")
                    if q_uid:
                        sub = str(request.state.identity.get("sub"))
                        if request.state.identity.get("method") != "api_key" and sub != q_uid:
                            from fastapi.responses import JSONResponse
                            return JSONResponse({"detail": "Forbidden: user mismatch"}, status_code=403)
                if "users" in parts:
                    idx = parts.index("users")
                    claimed = parts[idx + 1]
                    sub = str(request.state.identity.get("sub"))
                    # Allow api_key method to bypass ownership
                    if request.state.identity.get("method") != "api_key" and sub != claimed:
                        from fastapi.responses import JSONResponse
                        return JSONResponse({"detail": "Forbidden: user mismatch"}, status_code=403)
            except HTTPException:
                raise
            except Exception:
                pass
            return await call_next(request)

    app.add_middleware(_AuthMiddleware)

    # Token issuance endpoints (optional)
    if allow_issuer_endpoints and issuer_cfg and issuer_cfg.enabled:
        if issuer_cfg.algorithm == "HS256" and not issuer_cfg.hs256_secret:
            raise RuntimeError("HS256 issuer requires hs256_secret")
        router = APIRouter()

        @router.post("/auth/register")
        async def register(username: str, password: str):
            if not auth_store:
                raise HTTPException(status_code=400, detail="SQL store not configured")
            uid = auth_store.create_user(username, password)
            return {"user_id": uid}

        @router.post("/auth/token")
        async def token_grant(grant_type: str = "password", username: Optional[str] = None, password: Optional[str] = None,
                              user_id: Optional[str] = None, fingerprint: Optional[str] = None):
            sub: Optional[str] = None
            if grant_type == "password":
                if not auth_store or not username or password is None:
                    raise HTTPException(status_code=400, detail="invalid_request")
                uid = auth_store.authenticate_basic(username, password)
                if not uid:
                    raise HTTPException(status_code=401, detail="invalid_grant")
                sub = uid
            elif grant_type == "client_credentials":
                # For simplicity map to provided user_id
                if not user_id:
                    raise HTTPException(status_code=400, detail="invalid_request")
                sub = user_id
            else:
                raise HTTPException(status_code=400, detail="unsupported_grant_type")

            now = now_ts()
            access = {
                "iss": issuer_cfg.issuer,
                "aud": issuer_cfg.audience,
                "sub": sub,
                "iat": now,
                "nbf": now,
                "exp": now + issuer_cfg.access_ttl_seconds,
            }
            key = issuer_cfg.hs256_secret if issuer_cfg.algorithm == "HS256" else ""
            access_token = encode_jwt(access, algorithm=issuer_cfg.algorithm, key=key)

            refresh_token = None
            if auth_store:
                jti = auth_store.issue_refresh(sub, issuer_cfg.refresh_ttl_seconds, fingerprint=fingerprint)
                refresh_token = jti
            return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

        @router.post("/auth/refresh")
        async def refresh(user_id: str, refresh_token: str, fingerprint: Optional[str] = None):
            if not auth_store:
                raise HTTPException(status_code=400, detail="invalid_request")
            if not auth_store.verify_refresh(refresh_token, user_id, fingerprint=fingerprint):
                raise HTTPException(status_code=401, detail="invalid_grant")
            now = now_ts()
            access = {
                "iss": issuer_cfg.issuer,
                "aud": issuer_cfg.audience,
                "sub": user_id,
                "iat": now,
                "nbf": now,
                "exp": now + issuer_cfg.access_ttl_seconds,
            }
            key = issuer_cfg.hs256_secret if issuer_cfg.algorithm == "HS256" else ""
            access_token = encode_jwt(access, algorithm=issuer_cfg.algorithm, key=key)
            return {"access_token": access_token, "token_type": "bearer"}

        app.include_router(router)

    # API key management endpoints (require SQL store) — only if API keys are allowed
    if auth_store and allow_api_key:
        api_router = APIRouter()

        @api_router.post("/auth/api-keys")
        async def create_api_key(user_id: Optional[str] = None, name: Optional[str] = None):
            key_id, key_plain = auth_store.create_api_key(user_id=user_id, name=name)
            return {"id": key_id, "api_key": key_plain}

        @api_router.get("/auth/api-keys")
        async def list_api_keys():
            return auth_store.list_api_keys()

        @api_router.delete("/auth/api-keys/{key_id}")
        async def delete_api_key(key_id: str):
            auth_store.revoke_api_key(key_id)
            return {"ok": True}

        app.include_router(api_router)

    # /auth/me — identity echo endpoint
    who_router = APIRouter()

    @who_router.get("/auth/me")
    async def auth_me(request: Request):
        try:
            ident = await _authenticate(request)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)
        out = {"method": ident.get("method"), "sub": ident.get("sub")}
        if ident.get("username"):
            out["username"] = ident["username"]
        claims = ident.get("claims") or {}
        if claims:
            safe = {k: claims.get(k) for k in ("iss", "aud", "sub", "iat", "nbf", "exp") if k in claims}
            for k in ("scope", "scopes", "roles"):
                if k in claims:
                    safe[k] = claims[k]
            out["claims"] = safe
        return out

    app.include_router(who_router)
