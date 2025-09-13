from .config import AuthConfig, JwtIssuerConfig, JwtValidatorConfig
from .attach import attach_auth

__all__ = [
    "AuthConfig",
    "JwtIssuerConfig",
    "JwtValidatorConfig",
    "attach_auth",
]

# Safe verify_refresh monkey-patch for SQL store (and mirror behavior in Mongo store if needed)
try:
    from datetime import datetime, timezone
    from typing import Optional
    from google_adk_extras.auth import sql_store as _sql_store

    def _safe_verify_refresh(self, jti: str, user_id: str, fingerprint: str | None = None) -> bool:  # type: ignore[override]
        try:
            with self.Session() as s:
                rt = s.query(_sql_store.RefreshToken).filter_by(jti=jti, user_id=user_id).first()
                if not rt or rt.revoked_at is not None:
                    return False
                exp = rt.expires_at
                if getattr(exp, "tzinfo", None) is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if exp <= now:
                    return False
                if fingerprint and rt.fingerprint and rt.fingerprint != fingerprint:
                    return False
                return True
        except Exception:
            return False

    _sql_store.AuthStore.verify_refresh = _safe_verify_refresh  # type: ignore[assignment]
except Exception:
    pass
