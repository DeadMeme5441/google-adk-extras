from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, Optional

# Lazy import PyJWT to keep this optional when auth is not used.
def _import_pyjwt():
    try:
        import jwt  # type: ignore
        from jwt import PyJWKClient  # type: ignore
        return jwt, PyJWKClient
    except Exception as e:
        raise ImportError(
            "PyJWT is required for JWT encode/decode. Install with: pip install PyJWT"
        ) from e


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def encode_jwt(payload: Dict[str, Any], *, algorithm: str, key: str, headers: Optional[Dict[str, Any]] = None) -> str:
    jwt, _PyJWKClient = _import_pyjwt()
    return jwt.encode(payload, key, algorithm=algorithm, headers=headers)


def decode_jwt(token: str, *, issuer: Optional[str] = None, audience: Optional[str] = None,
               jwks_url: Optional[str] = None, hs256_secret: Optional[str] = None) -> Dict[str, Any]:
    jwt, PyJWKClient = _import_pyjwt()
    options = {"verify_signature": True, "verify_exp": True, "verify_nbf": True}
    if jwks_url:
        jwk_client = PyJWKClient(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        return jwt.decode(token, signing_key, algorithms=["RS256", "ES256"], audience=audience, issuer=issuer, options=options)
    elif hs256_secret:
        return jwt.decode(token, hs256_secret, algorithms=["HS256"], audience=audience, issuer=issuer, options=options)
    else:
        raise ValueError("No validation method configured (jwks_url or hs256_secret required)")


def now_ts() -> int:
    return int(time.time())

