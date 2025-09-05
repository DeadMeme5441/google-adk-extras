"""Local folder-based artifact service implementation."""

import os
import json
import base64
from typing import Optional, List
from pathlib import Path
from datetime import datetime, timezone

from google.genai import types
from .base_custom_artifact_service import BaseCustomArtifactService


class LocalFolderArtifactService(BaseCustomArtifactService):
    """Local folder-based artifact service implementation.

    This service stores artifacts in the local file system with full versioning support.
    Each artifact is stored with its metadata in JSON format and binary data in separate files.
    """

    def __init__(self, base_directory: str = "./artifacts"):
        """Initialize the local folder artifact service.
        
        Args:
            base_directory: Base directory for storing artifacts. Defaults to "./artifacts".
        """
        super().__init__()
        self.base_directory = Path(base_directory)
        # Create base directory if it doesn't exist
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def _initialize_impl(self) -> None:
        """Initialize the file system artifact service.
        
        Ensures the base directory exists.
        """
        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def _cleanup_impl(self) -> None:
        """Clean up resources (no cleanup needed for file-based service)."""
        pass

    def _get_artifact_directory(self, app_name: str, user_id: str, session_id: str) -> Path:
        """Generate directory path for artifacts.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            
        Returns:
            Path to the artifact directory.
        """
        directory = self.base_directory / app_name / user_id / session_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _get_artifact_file_path(self, app_name: str, user_id: str, session_id: str, filename: str) -> Path:
        """Generate file path for artifact metadata.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file.
            
        Returns:
            Path to the metadata file.
        """
        directory = self._get_artifact_directory(app_name, user_id, session_id)
        return directory / f"{filename}.json"

    def _get_artifact_data_path(self, app_name: str, user_id: str, session_id: str, filename: str, version: int) -> Path:
        """Generate file path for artifact data.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file.
            version: The version number.
            
        Returns:
            Path to the data file.
        """
        directory = self._get_artifact_directory(app_name, user_id, session_id)
        return directory / f"{filename}.v{version}.data"

    def _serialize_blob(self, part: types.Part) -> tuple[bytes, str]:
        """Extract blob data and mime type from a Part.
        
        Args:
            part: The Part object containing the blob data.
            
        Returns:
            A tuple of (data, mime_type).
            
        Raises:
            ValueError: If the part type is not supported.
        """
        if part.inline_data:
            return part.inline_data.data, part.inline_data.mime_type or "application/octet-stream"
        else:
            raise ValueError("Only inline_data parts are supported")

    def _deserialize_blob(self, data: bytes, mime_type: str) -> types.Part:
        """Create a Part from blob data and mime type.
        
        Args:
            data: The binary data.
            mime_type: The MIME type of the data.
            
        Returns:
            A Part object containing the blob data.
        """
        blob = types.Blob(data=data, mime_type=mime_type)
        return types.Part(inline_data=blob)

    async def _save_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        artifact: types.Part,
    ) -> int:
        """Implementation of artifact saving.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file to save.
            artifact: The artifact to save.
            
        Returns:
            The version number of the saved artifact.
            
        Raises:
            RuntimeError: If saving the artifact fails.
            ValueError: If the artifact type is not supported.
        """
        try:
            # Extract blob data
            data, mime_type = self._serialize_blob(artifact)
            
            # Get the next version number
            metadata_file = self._get_artifact_file_path(app_name, user_id, session_id, filename)
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                version = len(metadata.get("versions", []))
            else:
                metadata = {
                    "app_name": app_name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "filename": filename,
                    "versions": []
                }
                version = 0
            
            # Save data to file
            data_file = self._get_artifact_data_path(app_name, user_id, session_id, filename, version)
            with open(data_file, 'wb') as f:
                f.write(data)
            
            # Update metadata
            version_info = {
                "version": version,
                "mime_type": mime_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "data_file": data_file.name
            }
            metadata["versions"].append(version_info)
            
            # Save metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return version
        except Exception as e:
            raise RuntimeError(f"Failed to save artifact: {e}")

    async def _load_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        """Implementation of artifact loading.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file to load.
            version: Optional version number to load. If not provided,
                the latest version will be loaded.
                
        Returns:
            The loaded artifact if found, None otherwise.
            
        Raises:
            RuntimeError: If loading the artifact fails.
        """
        try:
            # Load metadata
            metadata_file = self._get_artifact_file_path(app_name, user_id, session_id, filename)
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Determine version to load
            versions = metadata.get("versions", [])
            if not versions:
                return None
            
            if version is not None:
                # Find specific version
                version_info = None
                for v in versions:
                    if v["version"] == version:
                        version_info = v
                        break
                if not version_info:
                    return None
            else:
                # Load latest version
                version_info = versions[-1]
            
            # Load data
            data_file = self._get_artifact_directory(app_name, user_id, session_id) / version_info["data_file"]
            if not data_file.exists():
                return None
            
            with open(data_file, 'rb') as f:
                data = f.read()
            
            # Create Part from blob data
            return self._deserialize_blob(data, version_info["mime_type"])
        except Exception as e:
            raise RuntimeError(f"Failed to load artifact: {e}")

    async def _list_artifact_keys_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> List[str]:
        """Implementation of artifact key listing.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            
        Returns:
            A list of artifact keys (filenames).
            
        Raises:
            RuntimeError: If listing artifact keys fails.
        """
        try:
            directory = self._get_artifact_directory(app_name, user_id, session_id)
            
            # Find all metadata files
            artifact_keys = []
            if directory.exists():
                for file_path in directory.glob("*.json"):
                    # Extract filename from metadata file name (remove .json extension)
                    filename = file_path.name[:-5]  # Remove .json
                    artifact_keys.append(filename)
            
            return artifact_keys
        except Exception as e:
            raise RuntimeError(f"Failed to list artifact keys: {e}")

    async def _delete_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> None:
        """Implementation of artifact deletion.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file to delete.
            
        Raises:
            RuntimeError: If deleting the artifact fails.
        """
        try:
            # Load metadata to find all version files
            metadata_file = self._get_artifact_file_path(app_name, user_id, session_id, filename)
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Delete all version data files
                directory = self._get_artifact_directory(app_name, user_id, session_id)
                for version_info in metadata.get("versions", []):
                    data_file = directory / version_info["data_file"]
                    if data_file.exists():
                        data_file.unlink()
                
                # Delete metadata file
                metadata_file.unlink()
        except Exception as e:
            raise RuntimeError(f"Failed to delete artifact: {e}")

    async def _list_versions_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> List[int]:
        """Implementation of version listing.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file to list versions for.
            
        Returns:
            A list of version numbers.
            
        Raises:
            RuntimeError: If listing versions fails.
        """
        try:
            metadata_file = self._get_artifact_file_path(app_name, user_id, session_id, filename)
            
            if not metadata_file.exists():
                return []
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            versions = metadata.get("versions", [])
            return [v["version"] for v in versions]
        except Exception as e:
            raise RuntimeError(f"Failed to list versions: {e}")