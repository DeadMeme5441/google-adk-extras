"""S3-compatible artifact service implementation."""

import json
import base64
from typing import Optional, List
from datetime import datetime, timezone

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    raise ImportError(
        "Boto3 is required for S3ArtifactService. "
        "Install it with: pip install boto3"
    )

from google.genai import types
from .base_custom_artifact_service import BaseCustomArtifactService


class S3ArtifactService(BaseCustomArtifactService):
    """S3-compatible artifact service implementation.

    This service stores artifacts in AWS S3 or S3-compatible storage services.
    It supports versioning and works with any S3-compatible service including
    AWS S3, MinIO, Google Cloud Storage, etc.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        prefix: str = "adk-artifacts",
    ):
        """Initialize the S3 artifact service.
        
        Args:
            bucket_name: S3 bucket name.
            endpoint_url: S3 endpoint URL (for non-AWS S3 services like MinIO).
            region_name: AWS region name.
            aws_access_key_id: AWS access key ID.
            aws_secret_access_key: AWS secret access key.
            prefix: Prefix for artifact storage paths. Defaults to "adk-artifacts".
        """
        super().__init__()
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.prefix = prefix
        self.s3_client = None

    async def _initialize_impl(self) -> None:
        """Initialize the S3 client.
        
        Creates the S3 client and verifies the bucket exists (or creates it).
        
        Raises:
            RuntimeError: If S3 initialization fails.
            NoCredentialsError: If AWS credentials are not found.
        """
        try:
            # Create S3 client
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            
            # Verify bucket exists or create it
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    # Bucket doesn't exist, create it
                    if self.region_name:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )
                    else:
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    raise
        except NoCredentialsError:
            raise RuntimeError("AWS credentials not found. Please provide credentials.")
        except ClientError as e:
            raise RuntimeError(f"Failed to initialize S3 artifact service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up S3 client."""
        if self.s3_client:
            self.s3_client = None

    def _get_artifact_key(self, app_name: str, user_id: str, session_id: str, filename: str) -> str:
        """Generate S3 key for artifact metadata.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file.
            
        Returns:
            S3 key for the metadata file.
        """
        return f"{self.prefix}/{app_name}/{user_id}/{session_id}/{filename}.json"

    def _get_artifact_data_key(self, app_name: str, user_id: str, session_id: str, filename: str, version: int) -> str:
        """Generate S3 key for artifact data.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the file.
            version: The version number.
            
        Returns:
            S3 key for the data file.
        """
        return f"{self.prefix}/{app_name}/{user_id}/{session_id}/{filename}.v{version}.data"

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
            metadata_key = self._get_artifact_key(app_name, user_id, session_id, filename)
            
            try:
                # Try to load existing metadata
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                metadata = json.loads(response['Body'].read().decode('utf-8'))
                version = len(metadata.get("versions", []))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    # Metadata doesn't exist, create new
                    metadata = {
                        "app_name": app_name,
                        "user_id": user_id,
                        "session_id": session_id,
                        "filename": filename,
                        "versions": []
                    }
                    version = 0
                else:
                    raise
            
            # Save data to S3
            data_key = self._get_artifact_data_key(app_name, user_id, session_id, filename, version)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=data_key,
                Body=data
            )
            
            # Update metadata
            version_info = {
                "version": version,
                "mime_type": mime_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "data_key": data_key
            }
            metadata["versions"].append(version_info)
            
            # Save metadata to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2).encode('utf-8')
            )
            
            return version
        except ClientError as e:
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
            metadata_key = self._get_artifact_key(app_name, user_id, session_id, filename)
            
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                metadata = json.loads(response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return None
                else:
                    raise
            
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
            try:
                data_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=version_info["data_key"]
                )
                data = data_response['Body'].read()
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return None
                else:
                    raise
            
            # Create Part from blob data
            return self._deserialize_blob(data, version_info["mime_type"])
        except ClientError as e:
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
            # List objects with the prefix
            prefix = f"{self.prefix}/{app_name}/{user_id}/{session_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            artifact_keys = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    # Check if it's a metadata file
                    if key.endswith('.json') and key.startswith(prefix):
                        # Extract filename from metadata key
                        filename = key[len(prefix):-5]  # Remove prefix and .json extension
                        artifact_keys.append(filename)
            
            return artifact_keys
        except ClientError as e:
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
            metadata_key = self._get_artifact_key(app_name, user_id, session_id, filename)
            
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                metadata = json.loads(response['Body'].read().decode('utf-8'))
                
                # Delete all version data files
                for version_info in metadata.get("versions", []):
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=version_info["data_key"]
                    )
                
                # Delete metadata file
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=metadata_key
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    raise
        except ClientError as e:
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
            metadata_key = self._get_artifact_key(app_name, user_id, session_id, filename)
            
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                metadata = json.loads(response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return []
                else:
                    raise
            
            versions = metadata.get("versions", [])
            return [v["version"] for v in versions]
        except ClientError as e:
            raise RuntimeError(f"Failed to list versions: {e}")