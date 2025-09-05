"""Base class for custom artifact services."""

import abc
from typing import Optional, List

from google.adk.artifacts.base_artifact_service import BaseArtifactService
from google.genai import types


class BaseCustomArtifactService(BaseArtifactService, abc.ABC):
    """Base class for custom artifact services with common functionality."""

    def __init__(self):
        """Initialize the base custom artifact service."""
        super().__init__()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the artifact service.
        
        This method should be called before using the service to ensure
        any required setup (database connections, etc.) is complete.
        """
        if not self._initialized:
            await self._initialize_impl()
            self._initialized = True

    @abc.abstractmethod
    async def _initialize_impl(self) -> None:
        """Implementation of service initialization.
        
        This method should handle any setup required for the service to function,
        such as database connections, creating tables, directories, etc.
        """
        pass

    async def cleanup(self) -> None:
        """Clean up resources used by the artifact service.
        
        This method should be called when the service is no longer needed
        to ensure proper cleanup of resources.
        """
        if self._initialized:
            await self._cleanup_impl()
            self._initialized = False

    @abc.abstractmethod
    async def _cleanup_impl(self) -> None:
        """Implementation of service cleanup.
        
        This method should handle any cleanup required for the service,
        such as closing database connections.
        """
        pass

    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        artifact: types.Part,
    ) -> int:
        """Save an artifact."""
        if not self._initialized:
            await self.initialize()
        return await self._save_artifact_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            artifact=artifact,
        )

    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        """Load an artifact."""
        if not self._initialized:
            await self.initialize()
        return await self._load_artifact_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            version=version,
        )

    async def list_artifact_keys(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> List[str]:
        """List artifact keys."""
        if not self._initialized:
            await self.initialize()
        return await self._list_artifact_keys_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )

    async def delete_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> None:
        """Delete an artifact."""
        if not self._initialized:
            await self.initialize()
        await self._delete_artifact_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
        )

    async def list_versions(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> List[int]:
        """List versions of an artifact."""
        if not self._initialized:
            await self.initialize()
        return await self._list_versions_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
        )

    @abc.abstractmethod
    async def _save_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        artifact: types.Part,
    ) -> int:
        """Implementation of artifact saving."""
        pass

    @abc.abstractmethod
    async def _load_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        """Implementation of artifact loading."""
        pass

    @abc.abstractmethod
    async def _list_artifact_keys_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> List[str]:
        """Implementation of artifact key listing."""
        pass

    @abc.abstractmethod
    async def _delete_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> None:
        """Implementation of artifact deletion."""
        pass

    @abc.abstractmethod
    async def _list_versions_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> List[int]:
        """Implementation of version listing."""
        pass