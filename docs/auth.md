# Auth (Optional)

Inbound API authentication is optional. If you don’t pass an `auth_config`, all routes are open (useful for local dev). When enabled, the middleware protects sensitive routes and enforces identity where appropriate.

Supported methods:
- API Key
  - Send `X-API-Key: <token>` header or `?api_key=<token>` query.
  - Keys can be static via config or issued/rotated via SQL‑backed endpoints.
- HTTP Basic
  - `Authorization: Basic base64(user:pass)`.
  - Checks an in‑memory map or the SQL users table when configured.
- Bearer JWT (validate)
  - Validate JWTs from OIDC providers (Google, Auth0, Okta, etc.) via JWKS.
  - Or use HS256 with a shared secret in dev.
- Bearer JWT (issue)
  - First‑party issuer backed by SQL; exposes `/auth/register`, `/auth/token`, `/auth/refresh`.

### Per-method gating (fine control)
Set these flags on `AuthConfig` to explicitly allow/deny methods:

- `allow_api_key: Optional[bool]` — True/False to force enable/disable. None (default) auto-enables if static keys or SQL store exist.
- `allow_basic: Optional[bool]` — True/False to force; None auto-enables if a basic user map or SQL store exists.
- `allow_bearer_jwt: Optional[bool]` — True/False to force; None auto-enables if `jwt_validator` is provided.
- `allow_issuer_endpoints: Optional[bool]` — True/False to force; None auto-enables if `jwt_issuer.enabled=True`.
- `allow_query_api_key: bool` — If False, disables `?api_key=` query usage (header only).

Example: Only JWT (OIDC), no API key or Basic
```python
auth = AuthConfig(
    enabled=True,
    jwt_validator=JwtValidatorConfig(jwks_url=..., issuer=..., audience=...),
    allow_api_key=False,
    allow_basic=False,
    allow_bearer_jwt=True,
)
```

### Who am I endpoint
- `GET /auth/me` — returns the authenticated identity as seen by the server:
  ```json
  {
    "method": "jwt|api_key|basic",
    "sub": "user-id-or-subject",
    "username": "optional",
    "claims": { "iss": "...", "aud": "...", "sub": "...", "iat": 0, "nbf": 0, "exp": 0, "scope|scopes|roles": "..." }
  }
  ```

## Quick examples

### Enable JWT validate only
```python
from google_adk_extras import AdkBuilder
from google_adk_extras.auth import AuthConfig, JwtValidatorConfig

auth = AuthConfig(
    enabled=True,
    jwt_validator=JwtValidatorConfig(
        jwks_url="https://YOUR_ISSUER/.well-known/jwks.json",
        issuer="https://YOUR_ISSUER",
        audience="your-api-audience",
    ),
)

app = AdkBuilder().with_agents_dir("./agents").build_fastapi_app()
```

### First‑party issuer + validate (HS256) and SQL store
```python
from google_adk_extras import AdkBuilder
from google_adk_extras.auth import AuthConfig, JwtIssuerConfig, JwtValidatorConfig

issuer = JwtIssuerConfig(
    enabled=True,
    issuer="https://local-issuer",
    audience="adk-api",
    algorithm="HS256",
    hs256_secret="topsecret",
    database_url="sqlite:///./auth.db",
)
validator = JwtValidatorConfig(issuer=issuer.issuer, audience=issuer.audience, hs256_secret=issuer.hs256_secret)

auth = AuthConfig(enabled=True, jwt_issuer=issuer, jwt_validator=validator)

app = AdkBuilder().with_agents_dir("./agents").build_fastapi_app()
```

### API key management endpoints (SQL store)
- `POST /auth/api-keys` → `{ id, api_key }` (plaintext shown once)
- `GET /auth/api-keys` → list metadata
- `DELETE /auth/api-keys/{id}` → revoke

Use `X-API-Key: <api_key>` (or `?api_key=`) to access protected routes.

## What’s protected
- Always: `POST /run`, `POST /run_sse`, `GET/POST/DELETE /apps/...`, `/debug/*`, `/builder/*`.
- Optional: `/list-apps` and `/apps/{app}/metrics-info` (toggled in `AuthConfig`).
- Ownership: when the URL contains `/users/{user_id}/...`, the `sub` from the token must match `user_id` (API key bypass permitted).

## Optional by design
- No‑auth is the default. Enable auth only when you’re ready.
- You can mix modes: e.g., JWT for users and API keys for automation.

```python
# Direct call if not using the builder
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.auth import AuthConfig
app = get_enhanced_fast_api_app(..., auth_config=AuthConfig(enabled=True, api_keys=["test"]))
```
