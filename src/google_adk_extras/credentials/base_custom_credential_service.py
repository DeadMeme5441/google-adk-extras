"""Base class for custom credential services."""

import abc
from typing import Optional

from google.adk.auth.credential_service.base_credential_service import BaseCredentialService, CallbackContext
from google.adk.auth import AuthConfig, AuthCredential


class BaseCustomCredentialService(BaseCredentialService, abc.ABC):
    """Base class for custom credential services with common functionality.

    This abstract base class provides a foundation for implementing custom
    credential services with automatic initialization and cleanup handling.
    """

    def __init__(self):
        """Initialize the base custom credential service."""
        super().__init__()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the credential service.
        
        This method should be called before using the service to ensure
        any required setup (connections, validations, etc.) is complete.
        
        Raises:
            RuntimeError: If initialization fails.
        """
        if not self._initialized:
            await self._initialize_impl()
            self._initialized = True

    @abc.abstractmethod
    async def _initialize_impl(self) -> None:
        """Implementation of service initialization.
        
        This method should handle any setup required for the service to function,
        such as validating credentials, establishing connections, etc.
        
        Raises:
            RuntimeError: If initialization fails.
        """
        pass

    async def cleanup(self) -> None:
        """Clean up resources used by the credential service.
        
        This method should be called when the service is no longer needed
        to ensure proper cleanup of any resources.
        """
        if self._initialized:
            await self._cleanup_impl()
            self._initialized = False

    async def _cleanup_impl(self) -> None:
        """Implementation of service cleanup.
        
        This method should handle cleanup of any resources used by the service.
        The default implementation does nothing, but subclasses can override
        to perform specific cleanup operations.
        """
        pass

    def _check_initialized(self) -> None:
        """Check if the service has been initialized.
        
        Raises:
            RuntimeError: If the service has not been initialized.
        """
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} must be initialized before use. "
                "Call await service.initialize() first."
            )

    @abc.abstractmethod
    async def load_credential(
        self,
        auth_config: AuthConfig,
        callback_context: CallbackContext,
    ) -> Optional[AuthCredential]:
        """Load the credential by auth config and current callback context.

        Args:
            auth_config: The auth config which contains the auth scheme and auth
                credential information. auth_config.get_credential_key will be used to
                build the key to load the credential.
            callback_context: The context of the current invocation when the tool is
                trying to load the credential.

        Returns:
            Optional[AuthCredential]: the credential saved in the store, or None if not found.
        """
        pass

    @abc.abstractmethod
    async def save_credential(
        self,
        auth_config: AuthConfig,
        callback_context: CallbackContext,
    ) -> None:
        """Save the exchanged_auth_credential in auth config.

        Args:
            auth_config: The auth config which contains the auth scheme and auth
                credential information. auth_config.get_credential_key will be used to
                build the key to save the credential.
            callback_context: The context of the current invocation when the tool is
                trying to save the credential.
        """
        pass