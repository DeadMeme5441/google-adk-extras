"""HTTP Basic Auth credential service implementation."""

from typing import Optional, Dict
import logging
import base64

from google.adk.auth.credential_service.session_state_credential_service import SessionStateCredentialService
from google.adk.auth.credential_service.base_credential_service import CallbackContext
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_credential import HttpAuth, HttpCredentials
from fastapi.openapi.models import HTTPBase

from .base_custom_credential_service import BaseCustomCredentialService

logger = logging.getLogger(__name__)


class HTTPBasicAuthCredentialService(BaseCustomCredentialService):
    """HTTP Basic Auth credential service for username/password authentication.
    
    This service manages HTTP Basic Authentication credentials, encoding username
    and password combinations for API authentication.
    
    Args:
        username: The username for basic authentication.
        password: The password for basic authentication.
        realm: Optional realm parameter for HTTP Basic Auth.
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = HTTPBasicAuthCredentialService(
            username="api_user",
            password="api_password",
            realm="API Access"
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
    
    Security Note:
        Basic Auth transmits credentials in base64 encoding, which is not encryption.
        Always use HTTPS when using Basic Auth to protect credentials in transit.
    """

    def __init__(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None,
        use_session_state: bool = True
    ):
        """Initialize the HTTP Basic Auth credential service.
        
        Args:
            username: Username for basic authentication.
            password: Password for basic authentication.
            realm: Optional realm for HTTP Basic Auth.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.username = username
        self.password = password
        self.realm = realm
        self.use_session_state = use_session_state
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    async def _initialize_impl(self) -> None:
        """Initialize the HTTP Basic Auth credential service.
        
        Validates the username and password configuration.
        
        Raises:
            ValueError: If username or password is missing.
        """
        if not self.username:
            raise ValueError("Username is required for HTTP Basic Auth")
        if not self.password:
            raise ValueError("Password is required for HTTP Basic Auth")
            
        logger.info(f"Initialized HTTP Basic Auth credential service for user: {self.username}")

    def encode_basic_auth(self, username: str, password: str) -> str:
        """Encode username and password for HTTP Basic Auth.
        
        Args:
            username: The username to encode.
            password: The password to encode.
            
        Returns:
            str: Base64 encoded credentials in format "Basic <encoded>".
        """
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
        return f"Basic {encoded_credentials}"

    def decode_basic_auth(self, auth_header: str) -> tuple[str, str]:
        """Decode HTTP Basic Auth header to extract username and password.
        
        Args:
            auth_header: The Authorization header value.
            
        Returns:
            tuple[str, str]: Tuple of (username, password).
            
        Raises:
            ValueError: If the auth header is invalid.
        """
        if not auth_header.startswith("Basic "):
            raise ValueError("Invalid Basic Auth header format")
            
        encoded_credentials = auth_header[6:]  # Remove "Basic " prefix
        try:
            credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = credentials.split(':', 1)
            return username, password
        except Exception as e:
            raise ValueError(f"Failed to decode Basic Auth credentials: {e}")

    def create_auth_config(self) -> AuthConfig:
        """Create an AuthConfig for HTTP Basic Authentication.
        
        Returns:
            AuthConfig: Configured auth config for HTTP Basic Auth.
        """
        self._check_initialized()
        
        # Create HTTP Basic auth scheme
        auth_scheme = HTTPBase(scheme="basic")
        
        # Create HTTP Basic credential
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.HTTP,
            http=HttpAuth(
                scheme="basic",
                credentials=HttpCredentials(
                    username=self.username,
                    password=self.password
                )
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
        """Load HTTP Basic Auth credential from storage.
        
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
        """Save HTTP Basic Auth credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved HTTP Basic Auth credential for user {callback_context._invocation_context.user_id}")

    def validate_credentials(self, test_username: str, test_password: str) -> bool:
        """Validate if provided credentials match the configured ones.
        
        Args:
            test_username: Username to validate.
            test_password: Password to validate.
            
        Returns:
            bool: True if credentials match, False otherwise.
        """
        self._check_initialized()
        return self.username == test_username and self.password == test_password

    def get_auth_header(self) -> str:
        """Get the Authorization header value for HTTP Basic Auth.
        
        Returns:
            str: The complete Authorization header value.
        """
        self._check_initialized()
        return self.encode_basic_auth(self.username, self.password)

    def get_credential_info(self) -> Dict[str, str]:
        """Get information about the configured credentials (without passwords).
        
        Returns:
            Dict[str, str]: Credential information (excluding sensitive data).
        """
        self._check_initialized()
        
        info = {
            "username": self.username,
            "auth_type": "HTTP Basic Auth",
            "password_set": bool(self.password)
        }
        
        if self.realm:
            info["realm"] = self.realm
            
        return info


class HTTPBasicAuthWithCredentialsService(BaseCustomCredentialService):
    """HTTP Basic Auth service that accepts multiple username/password pairs.
    
    This variant allows managing multiple sets of credentials, useful for
    scenarios where different users or contexts require different credentials.
    
    Args:
        credentials: Dictionary mapping usernames to passwords.
        default_username: Default username to use if not specified.
        realm: Optional realm parameter for HTTP Basic Auth.
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = HTTPBasicAuthWithCredentialsService(
            credentials={
                "admin": "admin_password",
                "user1": "user1_password",
                "api_client": "api_secret"
            },
            default_username="api_client"
        )
        await credential_service.initialize()
        ```
    """

    def __init__(
        self,
        credentials: Dict[str, str],
        default_username: Optional[str] = None,
        realm: Optional[str] = None,
        use_session_state: bool = True
    ):
        """Initialize the multi-credential HTTP Basic Auth service.
        
        Args:
            credentials: Dictionary of username -> password mappings.
            default_username: Default username to use.
            realm: Optional realm for HTTP Basic Auth.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.credentials = credentials.copy()
        self.default_username = default_username or (list(credentials.keys())[0] if credentials else None)
        self.realm = realm
        self.use_session_state = use_session_state
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    async def _initialize_impl(self) -> None:
        """Initialize the multi-credential HTTP Basic Auth service.
        
        Validates that credentials are provided and default username exists.
        
        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.credentials:
            raise ValueError("At least one username/password pair is required")
        if self.default_username and self.default_username not in self.credentials:
            raise ValueError(f"Default username '{self.default_username}' not found in credentials")
        if not self.default_username:
            raise ValueError("Default username is required when multiple credentials are provided")
            
        logger.info(f"Initialized HTTP Basic Auth service with {len(self.credentials)} credential sets")

    def create_auth_config(self, username: Optional[str] = None) -> AuthConfig:
        """Create an AuthConfig for HTTP Basic Authentication.
        
        Args:
            username: Username to use. If None, uses default_username.
            
        Returns:
            AuthConfig: Configured auth config for HTTP Basic Auth.
            
        Raises:
            ValueError: If username is not found in credentials.
        """
        self._check_initialized()
        
        username = username or self.default_username
        if username not in self.credentials:
            raise ValueError(f"Username '{username}' not found in credentials")
            
        password = self.credentials[username]
        
        # Create HTTP Basic auth scheme
        auth_scheme = HTTPBase(scheme="basic")
        
        # Create HTTP Basic credential
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.HTTP,
            http=HttpAuth(
                scheme="basic",
                credentials=HttpCredentials(
                    username=username,
                    password=password
                )
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
        """Load HTTP Basic Auth credential from storage.
        
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
        """Save HTTP Basic Auth credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved HTTP Basic Auth credential for user {callback_context._invocation_context.user_id}")

    def get_available_usernames(self) -> list[str]:
        """Get list of available usernames.
        
        Returns:
            list[str]: List of configured usernames.
        """
        return list(self.credentials.keys())