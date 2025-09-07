"""Custom credential service implementations for Google ADK.

Optional services are imported lazily to avoid import-time failures when
their third-party dependencies are not installed.
"""

from .base_custom_credential_service import BaseCustomCredentialService
from .google_oauth2_credential_service import GoogleOAuth2CredentialService
from .github_oauth2_credential_service import GitHubOAuth2CredentialService
from .microsoft_oauth2_credential_service import MicrosoftOAuth2CredentialService
from .x_oauth2_credential_service import XOAuth2CredentialService
from .http_basic_auth_credential_service import (
    HTTPBasicAuthCredentialService,
    HTTPBasicAuthWithCredentialsService,
)

# Optional: JWT (requires PyJWT)
try:
    from .jwt_credential_service import JWTCredentialService  # type: ignore
except Exception:  # ImportError or transitive import errors
    JWTCredentialService = None  # type: ignore

__all__ = [
    "BaseCustomCredentialService",
    "GoogleOAuth2CredentialService",
    "GitHubOAuth2CredentialService",
    "MicrosoftOAuth2CredentialService",
    "XOAuth2CredentialService",
    "HTTPBasicAuthCredentialService",
    "HTTPBasicAuthWithCredentialsService",
]

if JWTCredentialService is not None:
    __all__.append("JWTCredentialService")
