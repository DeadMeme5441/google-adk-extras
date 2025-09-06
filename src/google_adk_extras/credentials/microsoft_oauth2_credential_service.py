"""Microsoft OAuth2 credential service implementation."""

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


class MicrosoftOAuth2CredentialService(BaseCustomCredentialService):
    """Microsoft OAuth2 credential service for handling Microsoft authentication flows.
    
    This service provides pre-configured OAuth2 flows for Microsoft Graph API including
    Outlook, Teams, OneDrive, and other Microsoft 365 services.
    
    Args:
        tenant_id: The Azure AD tenant ID. Use "common" for multi-tenant applications.
        client_id: The Microsoft OAuth2 client ID from Azure AD App Registration.
        client_secret: The Microsoft OAuth2 client secret from Azure AD App Registration.
        scopes: List of OAuth2 scopes to request. Common scopes include:
            - "User.Read" - Read user profile
            - "Mail.Read" - Read user's mail
            - "Mail.ReadWrite" - Read and write user's mail
            - "Calendars.Read" - Read user's calendars
            - "Calendars.ReadWrite" - Read and write user's calendars
            - "Files.Read" - Read user's files
            - "Files.ReadWrite" - Read and write user's files
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = MicrosoftOAuth2CredentialService(
            tenant_id="common",  # or specific tenant ID
            client_id="your-azure-client-id",
            client_secret="your-azure-client-secret",
            scopes=["User.Read", "Mail.Read", "Calendars.ReadWrite"]
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

    # Microsoft OAuth2 endpoints (v2.0)
    def _get_auth_url(self, tenant_id: str) -> str:
        """Get the Microsoft OAuth2 authorization URL for the tenant."""
        return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    
    def _get_token_url(self, tenant_id: str) -> str:
        """Get the Microsoft OAuth2 token URL for the tenant."""
        return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    # Common Microsoft Graph API scopes
    COMMON_SCOPES = {
        # User and profile scopes
        "User.Read": "Read user profile",
        "User.ReadWrite": "Read and write user profile",
        "User.ReadBasic.All": "Read basic profiles of all users",
        "User.Read.All": "Read all users' full profiles",
        "User.ReadWrite.All": "Read and write all users' full profiles",
        
        # Mail scopes
        "Mail.Read": "Read user mail",
        "Mail.ReadWrite": "Read and write user mail", 
        "Mail.Send": "Send mail as user",
        "Mail.Read.Shared": "Read user and shared mail",
        "Mail.ReadWrite.Shared": "Read and write user and shared mail",
        
        # Calendar scopes
        "Calendars.Read": "Read user calendars",
        "Calendars.ReadWrite": "Read and write user calendars",
        "Calendars.Read.Shared": "Read user and shared calendars",
        "Calendars.ReadWrite.Shared": "Read and write user and shared calendars",
        
        # Files and OneDrive scopes
        "Files.Read": "Read user files",
        "Files.ReadWrite": "Read and write user files",
        "Files.Read.All": "Read all files that user can access",
        "Files.ReadWrite.All": "Read and write all files that user can access",
        "Sites.Read.All": "Read items in all site collections",
        "Sites.ReadWrite.All": "Read and write items in all site collections",
        
        # Groups and Teams scopes
        "Group.Read.All": "Read all groups",
        "Group.ReadWrite.All": "Read and write all groups",
        "Team.ReadBasic.All": "Read names and descriptions of teams",
        "TeamSettings.Read.All": "Read all teams' settings",
        "TeamSettings.ReadWrite.All": "Read and write all teams' settings",
        
        # Directory scopes
        "Directory.Read.All": "Read directory data",
        "Directory.ReadWrite.All": "Read and write directory data",
        
        # Application scopes
        "Application.Read.All": "Read all applications",
        "Application.ReadWrite.All": "Read and write all applications",
        
        # OpenID Connect scopes
        "openid": "OpenID Connect sign-in",
        "email": "View user's email address",
        "profile": "View user's basic profile",
        "offline_access": "Maintain access to data you have given access to"
    }

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        use_session_state: bool = True
    ):
        """Initialize the Microsoft OAuth2 credential service.
        
        Args:
            tenant_id: Azure AD tenant ID or "common" for multi-tenant.
            client_id: Microsoft OAuth2 client ID.
            client_secret: Microsoft OAuth2 client secret.
            scopes: List of OAuth2 scopes to request.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["User.Read", "Mail.Read"]
        self.use_session_state = use_session_state
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    async def _initialize_impl(self) -> None:
        """Initialize the Microsoft OAuth2 credential service.
        
        Validates the client credentials and sets up the OAuth2 auth scheme.
        
        Raises:
            ValueError: If required parameters are missing.
        """
        if not self.tenant_id:
            raise ValueError("Microsoft OAuth2 tenant_id is required")
        if not self.client_id:
            raise ValueError("Microsoft OAuth2 client_id is required")
        if not self.client_secret:
            raise ValueError("Microsoft OAuth2 client_secret is required")
        if not self.scopes:
            raise ValueError("At least one OAuth2 scope is required")
            
        # Validate scopes against known Microsoft scopes
        unknown_scopes = set(self.scopes) - set(self.COMMON_SCOPES.keys())
        if unknown_scopes:
            logger.warning(f"Unknown Microsoft OAuth2 scopes: {unknown_scopes}")
            
        logger.info(f"Initialized Microsoft OAuth2 credential service for tenant {self.tenant_id} with scopes: {self.scopes}")

    def create_auth_config(self) -> AuthConfig:
        """Create an AuthConfig for Microsoft OAuth2 authentication.
        
        Returns:
            AuthConfig: Configured auth config for Microsoft OAuth2 flow.
        """
        self._check_initialized()
        
        # Create OAuth2 auth scheme
        auth_scheme = OAuth2(
            flows=OAuthFlows(
                authorizationCode=OAuthFlowAuthorizationCode(
                    authorizationUrl=self._get_auth_url(self.tenant_id),
                    tokenUrl=self._get_token_url(self.tenant_id),
                    scopes={
                        scope: self.COMMON_SCOPES.get(scope, f"Microsoft Graph scope: {scope}")
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
        """Load Microsoft OAuth2 credential from storage.
        
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
        """Save Microsoft OAuth2 credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved Microsoft OAuth2 credential for user {callback_context._invocation_context.user_id} in tenant {self.tenant_id}")

    def get_supported_scopes(self) -> dict:
        """Get dictionary of supported Microsoft OAuth2 scopes and their descriptions.
        
        Returns:
            dict: Mapping of scope names to descriptions.
        """
        return self.COMMON_SCOPES.copy()