"""Custom artifact service implementations for Google ADK.

Optional backends are imported lazily based on installed dependencies.
"""

from .base_custom_artifact_service import BaseCustomArtifactService

try:
    from .sql_artifact_service import SQLArtifactService  # type: ignore
except Exception:
    SQLArtifactService = None  # type: ignore

try:
    from .mongo_artifact_service import MongoArtifactService  # type: ignore
except Exception:
    MongoArtifactService = None  # type: ignore

from .local_folder_artifact_service import LocalFolderArtifactService

try:
    from .s3_artifact_service import S3ArtifactService  # type: ignore
except Exception:
    S3ArtifactService = None  # type: ignore

__all__ = ["BaseCustomArtifactService", "LocalFolderArtifactService"]
for _name in ("SQLArtifactService", "MongoArtifactService", "S3ArtifactService"):
    if globals().get(_name) is not None:
        __all__.append(_name)
