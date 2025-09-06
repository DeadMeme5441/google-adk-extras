"""X (Twitter) OAuth2 credential service implementation."""

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


class XOAuth2CredentialService(BaseCustomCredentialService):
    """X (Twitter) OAuth2 credential service for handling X API authentication flows.
    
    This service provides pre-configured OAuth2 flows for X API v2 including
    reading tweets, posting content, and managing user data.
    
    Args:
        client_id: The X OAuth2 client ID from X Developer Portal.
        client_secret: The X OAuth2 client secret from X Developer Portal.
        scopes: List of OAuth2 scopes to request. Common scopes include:
            - "tweet.read" - Read tweets
            - "tweet.write" - Write tweets
            - "tweet.moderate.write" - Moderate tweets
            - "users.read" - Read user information
            - "follows.read" - Read follows information
            - "follows.write" - Manage follows
            - "offline.access" - Maintain access when user is offline
            - "space.read" - Read Spaces information
            - "mute.read" - Read muted accounts
            - "mute.write" - Manage muted accounts
            - "like.read" - Read likes information
            - "like.write" - Manage likes
            - "list.read" - Read list information
            - "list.write" - Manage lists
            - "block.read" - Read blocked accounts
            - "block.write" - Manage blocked accounts
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = XOAuth2CredentialService(
            client_id="your-x-client-id",
            client_secret="your-x-client-secret",
            scopes=["tweet.read", "tweet.write", "users.read", "offline.access"]
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

    # X OAuth2 endpoints
    X_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    
    # Common X OAuth2 scopes
    COMMON_SCOPES = {
        # Tweet scopes
        "tweet.read": "Read tweets",
        "tweet.write": "Write tweets",
        "tweet.moderate.write": "Hide and unhide replies to your tweets",
        
        # User scopes
        "users.read": "Read user profile information",
        
        # Follows scopes
        "follows.read": "Read who a user is following or who is following a user",
        "follows.write": "Follow and unfollow other users",
        
        # Offline access
        "offline.access": "Maintain access to accounts when users are offline",
        
        # Space scopes
        "space.read": "Read Spaces information",
        
        # Mute scopes
        "mute.read": "Read muted accounts",
        "mute.write": "Mute and unmute accounts",
        
        # Like scopes
        "like.read": "Read liked tweets",
        "like.write": "Like and unlike tweets",
        
        # List scopes
        "list.read": "Read list information",
        "list.write": "Create and manage lists",
        
        # Block scopes
        "block.read": "Read blocked accounts",
        "block.write": "Block and unblock accounts",
        
        # Bookmark scopes
        "bookmark.read": "Read bookmarked tweets",
        "bookmark.write": "Bookmark and unbookmark tweets",
        
        # Direct message scopes
        "dm.read": "Read direct messages",
        "dm.write": "Send direct messages",
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        use_session_state: bool = True
    ):
        """Initialize the X OAuth2 credential service.
        
        Args:
            client_id: X OAuth2 client ID.
            client_secret: X OAuth2 client secret.
            scopes: List of OAuth2 scopes to request.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["tweet.read", "users.read", "offline.access"]
        self.use_session_state = use_session_state
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    async def _initialize_impl(self) -> None:
        """Initialize the X OAuth2 credential service.
        
        Validates the client credentials and sets up the OAuth2 auth scheme.
        
        Raises:
            ValueError: If client_id or client_secret is missing.
        """
        if not self.client_id:
            raise ValueError("X OAuth2 client_id is required")
        if not self.client_secret:
            raise ValueError("X OAuth2 client_secret is required")
        if not self.scopes:
            raise ValueError("At least one OAuth2 scope is required")
            
        # Validate scopes against known X scopes
        unknown_scopes = set(self.scopes) - set(self.COMMON_SCOPES.keys())
        if unknown_scopes:
            logger.warning(f"Unknown X OAuth2 scopes: {unknown_scopes}")
            
        logger.info(f"Initialized X OAuth2 credential service with scopes: {self.scopes}")

    def create_auth_config(self) -> AuthConfig:
        """Create an AuthConfig for X OAuth2 authentication.
        
        Returns:
            AuthConfig: Configured auth config for X OAuth2 flow.
        """
        self._check_initialized()
        
        # Create OAuth2 auth scheme
        auth_scheme = OAuth2(
            flows=OAuthFlows(
                authorizationCode=OAuthFlowAuthorizationCode(
                    authorizationUrl=self.X_AUTH_URL,
                    tokenUrl=self.X_TOKEN_URL,
                    scopes={
                        scope: self.COMMON_SCOPES.get(scope, f"X API scope: {scope}")
                        for scope in self.scopes
                    }
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
        """Load X OAuth2 credential from storage.
        
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
        """Save X OAuth2 credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved X OAuth2 credential for user {callback_context._invocation_context.user_id}")

    def get_supported_scopes(self) -> dict:
        """Get dictionary of supported X OAuth2 scopes and their descriptions.
        
        Returns:
            dict: Mapping of scope names to descriptions.
        """
        return self.COMMON_SCOPES.copy()