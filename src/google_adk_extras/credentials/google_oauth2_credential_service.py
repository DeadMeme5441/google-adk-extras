"""Google OAuth2 credential service implementation."""

from typing import Optional, List
import logging

from google.adk.auth.credential_service.session_state_credential_service import SessionStateCredentialService
from google.adk.auth.credential_service.base_credential_service import CallbackContext
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_credential import OAuth2Auth
from fastapi.openapi.models import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode, OAuthFlows

from .base_custom_credential_service import BaseCustomCredentialService

logger = logging.getLogger(__name__)


class GoogleOAuth2CredentialService(BaseCustomCredentialService):
    """Google OAuth2 credential service for handling Google authentication flows.
    
    This service provides pre-configured OAuth2 flows for Google services including
    Gmail, Calendar, Drive, and other Google APIs.
    
    Args:
        client_id: The Google OAuth2 client ID from Google Cloud Console.
        client_secret: The Google OAuth2 client secret from Google Cloud Console.
        scopes: List of OAuth2 scopes to request. Common scopes include:
            - "openid" - OpenID Connect authentication
            - "email" - Access to email address
            - "profile" - Access to basic profile info
            - "https://www.googleapis.com/auth/calendar" - Google Calendar access
            - "https://www.googleapis.com/auth/gmail.readonly" - Gmail read access
            - "https://www.googleapis.com/auth/drive" - Google Drive access
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = GoogleOAuth2CredentialService(
            client_id="your-client-id.apps.googleusercontent.com",
            client_secret="your-client-secret",
            scopes=["openid", "email", "https://www.googleapis.com/auth/calendar"]
        )
        await credential_service.initialize()
        
        # Use with Runner
        runner = Runner(
            agent=agent,
            session_service=session_service,
            credential_service=credential_service,
            app_name="my_app"
        )
        ```
    """

    # Google OAuth2 endpoints
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    # Common Google OAuth2 scopes
    COMMON_SCOPES = {
        "openid": "OpenID Connect authentication",
        "email": "Access to email address", 
        "profile": "Access to basic profile information",
        "calendar": "https://www.googleapis.com/auth/calendar",
        "calendar.readonly": "https://www.googleapis.com/auth/calendar.readonly",
        "gmail.readonly": "https://www.googleapis.com/auth/gmail.readonly",
        "gmail.modify": "https://www.googleapis.com/auth/gmail.modify",
        "drive": "https://www.googleapis.com/auth/drive",
        "drive.readonly": "https://www.googleapis.com/auth/drive.readonly",
        "cloud-platform": "https://www.googleapis.com/auth/cloud-platform",
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        use_session_state: bool = True
    ):
        """Initialize the Google OAuth2 credential service.
        
        Args:
            client_id: Google OAuth2 client ID.
            client_secret: Google OAuth2 client secret.
            scopes: List of OAuth2 scopes to request.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["openid", "email", "profile"]
        self.use_session_state = use_session_state
        
        # Resolve scope shortcuts to full URLs
        self._resolved_scopes = self._resolve_scopes(self.scopes)
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    def _resolve_scopes(self, scopes: List[str]) -> List[str]:
        """Resolve scope shortcuts to full Google OAuth2 scope URLs.
        
        Args:
            scopes: List of scope names or URLs.
            
        Returns:
            List of resolved scope URLs.
        """
        resolved = []
        for scope in scopes:
            if scope in self.COMMON_SCOPES:
                resolved_scope = self.COMMON_SCOPES[scope]
                # If the value is a URL, use it; otherwise it's just a description
                if resolved_scope.startswith('https://'):
                    resolved.append(resolved_scope)
                else:
                    resolved.append(scope)
            else:
                resolved.append(scope)
        return resolved

    async def _initialize_impl(self) -> None:
        """Initialize the Google OAuth2 credential service.
        
        Validates the client credentials and sets up the OAuth2 auth scheme.
        
        Raises:
            ValueError: If client_id or client_secret is missing.
        """
        if not self.client_id:
            raise ValueError("Google OAuth2 client_id is required")
        if not self.client_secret:
            raise ValueError("Google OAuth2 client_secret is required")
        if not self._resolved_scopes:
            raise ValueError("At least one OAuth2 scope is required")
            
        logger.info(f"Initialized Google OAuth2 credential service with scopes: {self._resolved_scopes}")

    def create_auth_config(self) -> AuthConfig:
        """Create an AuthConfig for Google OAuth2 authentication.
        
        Returns:
            AuthConfig: Configured auth config for Google OAuth2 flow.
        """
        self._check_initialized()
        
        # Create OAuth2 auth scheme
        auth_scheme = OAuth2(
            flows=OAuthFlows(
                authorizationCode=OAuthFlowAuthorizationCode(
                    authorizationUrl=self.GOOGLE_AUTH_URL,
                    tokenUrl=self.GOOGLE_TOKEN_URL,
                    scopes={scope: f"Access to {scope}" for scope in self._resolved_scopes}
                )
            )
        )
        
        # Create OAuth2 credential
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2,
            oauth2=OAuth2Auth(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        )
        
        return AuthConfig(
            auth_scheme=auth_scheme,
            raw_auth_credential=auth_credential
        )

    async def load_credential(
        self,
        auth_config: AuthConfig,
        callback_context: CallbackContext,
    ) -> Optional[AuthCredential]:
        """Load Google OAuth2 credential from storage.
        
        Args:
            auth_config: The auth config containing credential key information.
            callback_context: The current callback context.
            
        Returns:
            Optional[AuthCredential]: The stored credential or None if not found.
        """
        self._check_initialized()
        return await self._storage_service.load_credential(auth_config, callback_context)

    async def save_credential(
        self,
        auth_config: AuthConfig,
        callback_context: CallbackContext,
    ) -> None:
        """Save Google OAuth2 credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved Google OAuth2 credential for user {callback_context._invocation_context.user_id}")

    def get_supported_scopes(self) -> dict:
        """Get dictionary of supported Google OAuth2 scopes and their descriptions.
        
        Returns:
            dict: Mapping of scope names to descriptions.
        """
        return self.COMMON_SCOPES.copy()