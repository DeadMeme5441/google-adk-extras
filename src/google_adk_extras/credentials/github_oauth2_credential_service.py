"""GitHub OAuth2 credential service implementation."""

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


class GitHubOAuth2CredentialService(BaseCustomCredentialService):
    """GitHub OAuth2 credential service for handling GitHub authentication flows.
    
    This service provides pre-configured OAuth2 flows for GitHub APIs including
    repository access, user information, and organization management.
    
    Args:
        client_id: The GitHub OAuth2 client ID from GitHub Developer Settings.
        client_secret: The GitHub OAuth2 client secret from GitHub Developer Settings.
        scopes: List of OAuth2 scopes to request. Common scopes include:
            - "user" - Access to user profile information
            - "user:email" - Access to user email addresses
            - "repo" - Full access to repositories
            - "public_repo" - Access to public repositories only
            - "admin:org" - Full access to organization data
            - "read:org" - Read access to organization data
            - "notifications" - Access to notifications
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = GitHubOAuth2CredentialService(
            client_id="your-github-client-id",
            client_secret="your-github-client-secret", 
            scopes=["user", "repo", "read:org"]
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

    # GitHub OAuth2 endpoints
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    
    # Common GitHub OAuth2 scopes
    COMMON_SCOPES = {
        "user": "Access to user profile information",
        "user:email": "Access to user email addresses", 
        "user:follow": "Access to follow/unfollow users",
        "repo": "Full access to public and private repositories",
        "public_repo": "Access to public repositories only",
        "repo:status": "Access to commit status",
        "repo_deployment": "Access to deployment status",
        "admin:org": "Full control of orgs and teams, read/write org projects",
        "write:org": "Read and write access to organization membership and projects",
        "read:org": "Read-only access to organization membership and projects",
        "admin:public_key": "Full control of user public keys",
        "write:public_key": "Write access to user public keys",
        "read:public_key": "Read access to user public keys",
        "admin:repo_hook": "Full control of repository hooks",
        "write:repo_hook": "Write access to repository hooks",
        "read:repo_hook": "Read access to repository hooks",
        "admin:org_hook": "Full control of organization hooks",
        "gist": "Write access to gists",
        "notifications": "Access to notifications",
        "delete_repo": "Delete repositories",
        "write:packages": "Upload packages to GitHub Package Registry",
        "read:packages": "Download packages from GitHub Package Registry",
        "workflow": "Update GitHub Action workflows"
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        use_session_state: bool = True
    ):
        """Initialize the GitHub OAuth2 credential service.
        
        Args:
            client_id: GitHub OAuth2 client ID.
            client_secret: GitHub OAuth2 client secret.
            scopes: List of OAuth2 scopes to request.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["user", "repo"]
        self.use_session_state = use_session_state
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    async def _initialize_impl(self) -> None:
        """Initialize the GitHub OAuth2 credential service.
        
        Validates the client credentials and sets up the OAuth2 auth scheme.
        
        Raises:
            ValueError: If client_id or client_secret is missing.
        """
        if not self.client_id:
            raise ValueError("GitHub OAuth2 client_id is required")
        if not self.client_secret:
            raise ValueError("GitHub OAuth2 client_secret is required")
        if not self.scopes:
            raise ValueError("At least one OAuth2 scope is required")
            
        # Validate scopes against known GitHub scopes
        unknown_scopes = set(self.scopes) - set(self.COMMON_SCOPES.keys())
        if unknown_scopes:
            logger.warning(f"Unknown GitHub OAuth2 scopes: {unknown_scopes}")
            
        logger.info(f"Initialized GitHub OAuth2 credential service with scopes: {self.scopes}")

    def create_auth_config(self) -> AuthConfig:
        """Create an AuthConfig for GitHub OAuth2 authentication.
        
        Returns:
            AuthConfig: Configured auth config for GitHub OAuth2 flow.
        """
        self._check_initialized()
        
        # Create OAuth2 auth scheme
        auth_scheme = OAuth2(
            flows=OAuthFlows(
                authorizationCode=OAuthFlowAuthorizationCode(
                    authorizationUrl=self.GITHUB_AUTH_URL,
                    tokenUrl=self.GITHUB_TOKEN_URL,
                    scopes={
                        scope: self.COMMON_SCOPES.get(scope, f"GitHub scope: {scope}")
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
        """Load GitHub OAuth2 credential from storage.
        
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
        """Save GitHub OAuth2 credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved GitHub OAuth2 credential for user {callback_context._invocation_context.user_id}")

    def get_supported_scopes(self) -> dict:
        """Get dictionary of supported GitHub OAuth2 scopes and their descriptions.
        
        Returns:
            dict: Mapping of scope names to descriptions.
        """
        return self.COMMON_SCOPES.copy()