from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JwtValidatorConfig:
    # Accept JWTs from external issuers (e.g., Google/Auth0/Okta) or our own issuer
    jwks_url: Optional[str] = None
    issuer: Optional[str] = None
    audience: Optional[str] = None
    # If you want to validate with an HS256 shared secret (tests/dev)
    hs256_secret: Optional[str] = None


@dataclass
class JwtIssuerConfig:
    # Configure our own issuer if we issue tokens
    enabled: bool = False
    issuer: str = "https://example-issuer"
    audience: str = "adk-api"
    algorithm: str = "HS256"  # HS256 or RS256/ES256 later
    hs256_secret: Optional[str] = None
    access_ttl_seconds: int = 3600
    refresh_ttl_seconds: int = 60 * 60 * 24 * 14
    # SQL store for users/refresh tokens
    database_url: Optional[str] = None  # e.g. sqlite:///auth.db


@dataclass
class AuthConfig:
    # Global toggle
    enabled: bool = False
    # Modes
    allow_no_auth: bool = False  # if True, bypass checks entirely
    api_keys: List[str] = field(default_factory=list)  # accepted API keys
    basic_users: dict[str, str] = field(default_factory=dict)  # username -> password (PBKDF2 hash or plaintext for tests)
    jwt_validator: Optional[JwtValidatorConfig] = None
    jwt_issuer: Optional[JwtIssuerConfig] = None
    # Per-method gates (None = auto, True/False = force on/off)
    allow_api_key: Optional[bool] = None
    allow_basic: Optional[bool] = None
    allow_bearer_jwt: Optional[bool] = None
    allow_issuer_endpoints: Optional[bool] = None
    # Header vs query controls for API key
    allow_query_api_key: bool = True
    # Route policy toggles
    protect_list_apps: bool = True
    protect_metrics: bool = True
    # Scopes are advisory; we currently validate presence of a token and subject. Extend as needed.
