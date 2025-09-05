"""SQL-based artifact service implementation using SQLAlchemy."""

import json
from typing import Optional, List
from datetime import datetime, timezone

try:
    from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, LargeBinary
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    raise ImportError(
        "SQLAlchemy is required for SQLArtifactService. "
        "Install it with: pip install sqlalchemy"
    )

from google.genai import types
from .base_custom_artifact_service import BaseCustomArtifactService


# Use the modern declarative_base import
Base = declarative_base()


class SQLArtifactModel(Base):
    """SQLAlchemy model for storing artifacts."""
    __tablename__ = 'adk_artifacts'

    # Composite primary key
    app_name = Column(String, primary_key=True)
    user_id = Column(String, primary_key=True)
    session_id = Column(String, primary_key=True)
    filename = Column(String, primary_key=True)
    version = Column(Integer, primary_key=True)
    
    # Artifact data
    mime_type = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)  # Blob data
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Metadata
    metadata_json = Column(Text, nullable=True)  # Additional metadata as JSON


class SQLArtifactService(BaseCustomArtifactService):
    """SQL-based artifact service implementation.

    This service stores artifacts in a SQL database using SQLAlchemy.
    It supports various SQL databases including SQLite, PostgreSQL, and MySQL.
    Artifacts are stored with full versioning support.
    """

    def __init__(self, database_url: str):
        """Initialize the SQL artifact service.
        
        Args:
            database_url: Database connection string (e.g., 'sqlite:///artifacts.db')
        """
        super().__init__()
        self.database_url = database_url
        self.engine: Optional[object] = None
        self.session_local: Optional[object] = None

    async def _initialize_impl(self) -> None:
        """Initialize the database connection and create tables.
        
        Raises:
            RuntimeError: If database initialization fails.
        """
        try:
            self.engine = create_engine(self.database_url)
            Base.metadata.create_all(self.engine)
            self.session_local = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to initialize SQL artifact service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up database connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self.session_local = None

    def _get_db_session(self):
        """Get a database session.
        
        Returns:
            A database session object.
            
        Raises:
            RuntimeError: If the service is not initialized.
        """
        if not self.session_local:
            raise RuntimeError("Service not initialized")
        return self.session_local()

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
            # If it's not inline data, we need to handle other types
            # For now, we'll raise an error - in a full implementation,
            # we'd need to handle other Part types
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
        db_session = self._get_db_session()
        try:
            # Extract blob data
            data, mime_type = self._serialize_blob(artifact)
            
            # Get the next version number
            latest_version_result = db_session.query(SQLArtifactModel).filter(
                SQLArtifactModel.app_name == app_name,
                SQLArtifactModel.user_id == user_id,
                SQLArtifactModel.session_id == session_id,
                SQLArtifactModel.filename == filename
            ).order_by(SQLArtifactModel.version.desc()).first()
            
            version = (latest_version_result.version + 1) if latest_version_result else 0
            
            # Create artifact model
            db_artifact = SQLArtifactModel(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=version,
                mime_type=mime_type,
                data=data
            )
            
            # Save to database
            db_session.add(db_artifact)
            db_session.commit()
            
            return version
        except SQLAlchemyError as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to save artifact: {e}")
        finally:
            db_session.close()

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
        db_session = self._get_db_session()
        try:
            query = db_session.query(SQLArtifactModel).filter(
                SQLArtifactModel.app_name == app_name,
                SQLArtifactModel.user_id == user_id,
                SQLArtifactModel.session_id == session_id,
                SQLArtifactModel.filename == filename
            )
            
            if version is not None:
                query = query.filter(SQLArtifactModel.version == version)
            else:
                # Get the latest version
                query = query.order_by(SQLArtifactModel.version.desc())
            
            db_artifact = query.first()
            
            if not db_artifact:
                return None
            
            # Create Part from blob data
            return self._deserialize_blob(db_artifact.data, db_artifact.mime_type)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to load artifact: {e}")
        finally:
            db_session.close()

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
        db_session = self._get_db_session()
        try:
            # Get distinct filenames
            filenames = db_session.query(SQLArtifactModel.filename).filter(
                SQLArtifactModel.app_name == app_name,
                SQLArtifactModel.user_id == user_id,
                SQLArtifactModel.session_id == session_id
            ).distinct().all()
            
            return [filename[0] for filename in filenames]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to list artifact keys: {e}")
        finally:
            db_session.close()

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
        db_session = self._get_db_session()
        try:
            # Delete all versions of the artifact
            db_session.query(SQLArtifactModel).filter(
                SQLArtifactModel.app_name == app_name,
                SQLArtifactModel.user_id == user_id,
                SQLArtifactModel.session_id == session_id,
                SQLArtifactModel.filename == filename
            ).delete()
            
            db_session.commit()
        except SQLAlchemyError as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to delete artifact: {e}")
        finally:
            db_session.close()

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
        db_session = self._get_db_session()
        try:
            versions = db_session.query(SQLArtifactModel.version).filter(
                SQLArtifactModel.app_name == app_name,
                SQLArtifactModel.user_id == user_id,
                SQLArtifactModel.session_id == session_id,
                SQLArtifactModel.filename == filename
            ).order_by(SQLArtifactModel.version.asc()).all()
            
            return [version[0] for version in versions]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to list versions: {e}")
        finally:
            db_session.close()