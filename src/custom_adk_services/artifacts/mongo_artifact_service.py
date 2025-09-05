"""MongoDB-based artifact service implementation."""

import json
from typing import Optional, List
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    raise ImportError(
        "PyMongo is required for MongoArtifactService. "
        "Install it with: pip install pymongo"
    )

from google.genai import types
from .base_custom_artifact_service import BaseCustomArtifactService


class MongoArtifactService(BaseCustomArtifactService):
    """MongoDB-based artifact service implementation."""

    def __init__(self, connection_string: str, database_name: str = "adk_artifacts"):
        """Initialize the MongoDB artifact service.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        super().__init__()
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None

    async def _initialize_impl(self) -> None:
        """Initialize the MongoDB connection."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db.artifacts
            
            # Create indexes for better performance
            self.collection.create_index([
                ("app_name", 1),
                ("user_id", 1),
                ("session_id", 1),
                ("filename", 1),
                ("version", 1)
            ])
        except PyMongoError as e:
            raise RuntimeError(f"Failed to initialize MongoDB artifact service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up MongoDB connections."""
        if self.client:
            self.client.close()
            self.client = None
        self.db = None
        self.collection = None

    def _serialize_blob(self, part: types.Part) -> tuple[bytes, str]:
        """Extract blob data and mime type from a Part."""
        if part.inline_data:
            return part.inline_data.data, part.inline_data.mime_type or "application/octet-stream"
        else:
            raise ValueError("Only inline_data parts are supported")

    def _deserialize_blob(self, data: bytes, mime_type: str) -> types.Part:
        """Create a Part from blob data and mime type."""
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
        """Implementation of artifact saving."""
        try:
            # Extract blob data
            data, mime_type = self._serialize_blob(artifact)
            
            # Get the next version number
            latest_version_doc = self.collection.find_one(
                {
                    "app_name": app_name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "filename": filename
                },
                sort=[("version", -1)]
            )
            
            version = (latest_version_doc["version"] + 1) if latest_version_doc else 0
            
            # Create document
            document = {
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id,
                "filename": filename,
                "version": version,
                "mime_type": mime_type,
                "data": data,
                "created_at": datetime.utcnow()
            }
            
            # Insert into MongoDB
            self.collection.insert_one(document)
            
            return version
        except PyMongoError as e:
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
        """Implementation of artifact loading."""
        try:
            query = {
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id,
                "filename": filename
            }
            
            if version is not None:
                query["version"] = version
                sort = None
            else:
                # Sort by version descending to get the latest
                sort = [("version", -1)]
            
            document = self.collection.find_one(query, sort=sort)
            
            if not document:
                return None
            
            # Create Part from blob data
            return self._deserialize_blob(document["data"], document["mime_type"])
        except PyMongoError as e:
            raise RuntimeError(f"Failed to load artifact: {e}")

    async def _list_artifact_keys_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> List[str]:
        """Implementation of artifact key listing."""
        try:
            # Get distinct filenames
            cursor = self.collection.distinct(
                "filename",
                {
                    "app_name": app_name,
                    "user_id": user_id,
                    "session_id": session_id
                }
            )
            
            return list(cursor)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to list artifact keys: {e}")

    async def _delete_artifact_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> None:
        """Implementation of artifact deletion."""
        try:
            # Delete all versions of the artifact
            self.collection.delete_many({
                "app_name": app_name,
                "user_id": user_id,
                "session_id": session_id,
                "filename": filename
            })
        except PyMongoError as e:
            raise RuntimeError(f"Failed to delete artifact: {e}")

    async def _list_versions_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
    ) -> List[int]:
        """Implementation of version listing."""
        try:
            cursor = self.collection.find(
                {
                    "app_name": app_name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "filename": filename
                },
                {"version": 1, "_id": 0}
            ).sort("version", 1)
            
            return [doc["version"] for doc in cursor]
        except PyMongoError as e:
            raise RuntimeError(f"Failed to list versions: {e}")