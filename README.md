# Custom ADK Services

This package provides custom implementations of Google ADK services for various storage backends.

## Available Services

### Session Services

#### 1. SQLSessionService
A session service that stores session data in SQL databases using SQLAlchemy.

**Features:**
- Supports all major SQL databases (SQLite, PostgreSQL, MySQL, etc.)
- Automatic table creation
- Full session management (create, get, list, delete, append events)

**Dependencies:**
```bash
pip install sqlalchemy
```

**Usage:**
```python
from custom_adk_services.sessions import SQLSessionService

# Initialize with database URL
service = SQLSessionService("sqlite:///./sessions.db")
# or
service = SQLSessionService("postgresql://user:password@localhost/dbname")

# Create a session
session = await service.create_session(
    app_name="my_app",
    user_id="user123",
    state={"theme": "dark"}
)
```

#### 2. MongoSessionService
A session service that stores session data in MongoDB.

**Features:**
- High-performance document storage
- Automatic index creation
- Full session management

**Dependencies:**
```bash
pip install pymongo
```

**Usage:**
```python
from custom_adk_services.sessions import MongoSessionService

# Initialize with connection string
service = MongoSessionService("mongodb://localhost:27017/")

# Create a session
session = await service.create_session(
    app_name="my_app",
    user_id="user123",
    state={"theme": "dark"}
)
```

#### 3. RedisSessionService
A session service that stores session data in Redis.

**Features:**
- Extremely fast in-memory storage
- Automatic key management
- Full session management

**Dependencies:**
```bash
pip install redis
```

**Usage:**
```python
from custom_adk_services.sessions import RedisSessionService

# Initialize with Redis connection details
service = RedisSessionService(host="localhost", port=6379, db=0)

# Create a session
session = await service.create_session(
    app_name="my_app",
    user_id="user123",
    state={"theme": "dark"}
)
```

#### 4. YamlFileSessionService
A session service that stores session data in YAML files.

**Features:**
- Human-readable file storage
- Hierarchical directory structure (app/user/session)
- No external dependencies (only PyYAML)

**Dependencies:**
```bash
pip install PyYAML
```

**Usage:**
```python
from custom_adk_services.sessions import YamlFileSessionService

# Initialize with base directory
service = YamlFileSessionService("./sessions")

# Create a session
session = await service.create_session(
    app_name="my_app",
    user_id="user123",
    state={"theme": "dark"}
)
```

### Artifact Services

#### 1. SQLArtifactService
An artifact service that stores artifacts in SQL databases using SQLAlchemy.

**Features:**
- Supports all major SQL databases (SQLite, PostgreSQL, MySQL, etc.)
- Automatic table creation
- Full artifact management with versioning
- Binary data storage in BLOB columns

**Dependencies:**
```bash
pip install sqlalchemy
```

**Usage:**
```python
from custom_adk_services.artifacts import SQLArtifactService
from google.genai.types import Part, Blob

# Initialize with database URL
service = SQLArtifactService("sqlite:///./artifacts.db")

# Create an artifact
data = b"Hello, World!"
blob = Blob(data=data, mime_type="text/plain")
artifact = Part(inline_data=blob)

# Save the artifact
version = await service.save_artifact(
    app_name="my_app",
    user_id="user123",
    session_id="session456",
    filename="hello.txt",
    artifact=artifact
)
```

#### 2. MongoArtifactService
An artifact service that stores artifacts in MongoDB.

**Features:**
- High-performance document storage
- Automatic index creation
- Full artifact management with versioning
- Binary data storage in GridFS or as binary fields

**Dependencies:**
```bash
pip install pymongo
```

**Usage:**
```python
from custom_adk_services.artifacts import MongoArtifactService
from google.genai.types import Part, Blob

# Initialize with connection string
service = MongoArtifactService("mongodb://localhost:27017/")

# Create an artifact
data = b"Hello, World!"
blob = Blob(data=data, mime_type="text/plain")
artifact = Part(inline_data=blob)

# Save the artifact
version = await service.save_artifact(
    app_name="my_app",
    user_id="user123",
    session_id="session456",
    filename="hello.txt",
    artifact=artifact
)
```

#### 3. LocalFolderArtifactService
An artifact service that stores artifacts as files in a local directory.

**Features:**
- File-based storage with hierarchical organization
- Full artifact management with versioning
- Human-readable metadata in JSON files
- Easy backup and inspection

**Dependencies:**
None (uses standard Python libraries)

**Usage:**
```python
from custom_adk_services.artifacts import LocalFolderArtifactService
from google.genai.types import Part, Blob

# Initialize with base directory
service = LocalFolderArtifactService("./artifacts")

# Create an artifact
data = b"Hello, World!"
blob = Blob(data=data, mime_type="text/plain")
artifact = Part(inline_data=blob)

# Save the artifact
version = await service.save_artifact(
    app_name="my_app",
    user_id="user123",
    session_id="session456",
    filename="hello.txt",
    artifact=artifact
)
```

#### 4. S3ArtifactService
An artifact service that stores artifacts in S3-compatible storage.

**Features:**
- Cloud storage with S3-compatible APIs
- Full artifact management with versioning
- Support for AWS S3 and other S3-compatible services (MinIO, etc.)
- Secure access with credentials

**Dependencies:**
```bash
pip install boto3
```

**Usage:**
```python
from custom_adk_services.artifacts import S3ArtifactService
from google.genai.types import Part, Blob

# Initialize with S3 configuration
service = S3ArtifactService(
    bucket_name="my-artifacts-bucket",
    endpoint_url="https://s3.amazonaws.com",  # For AWS
    # endpoint_url="http://localhost:9000",  # For MinIO
    region_name="us-east-1",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY"
)

# Create an artifact
data = b"Hello, World!"
blob = Blob(data=data, mime_type="text/plain")
artifact = Part(inline_data=blob)

# Save the artifact
version = await service.save_artifact(
    app_name="my_app",
    user_id="user123",
    session_id="session456",
    filename="hello.txt",
    artifact=artifact
)
```

## Installation

```bash
# First install Google ADK
pip install google-adk

# For all services
pip install sqlalchemy pymongo redis PyYAML boto3

# For specific services only
pip install sqlalchemy     # For SQL services only
pip install pymongo        # For MongoDB services only
pip install redis          # For Redis services only
pip install PyYAML         # For YAML file services only
pip install boto3          # For S3 services only
```

## Usage Examples

### Session Services Example
```python
import asyncio
from custom_adk_services.sessions import SQLSessionService

async def main():
    # Initialize service
    service = SQLSessionService("sqlite:///./sessions.db")
    
    try:
        # Create a session
        session = await service.create_session(
            app_name="my_app",
            user_id="user123",
            state={"theme": "dark", "language": "en"}
        )
        
        # Retrieve the session
        retrieved_session = await service.get_session(
            app_name="my_app",
            user_id="user123",
            session_id=session.id
        )
        
        print(f"Session state: {retrieved_session.state}")
        
    finally:
        # Clean up
        await service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Artifact Services Example
```python
import asyncio
from custom_adk_services.artifacts import LocalFolderArtifactService
from google.genai.types import Part, Blob

async def main():
    # Initialize service
    service = LocalFolderArtifactService("./artifacts")
    
    try:
        # Create an artifact
        data = b"Hello, World!"
        blob = Blob(data=data, mime_type="text/plain")
        artifact = Part(inline_data=blob)
        
        # Save the artifact
        version = await service.save_artifact(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="hello.txt",
            artifact=artifact
        )
        
        # Load the artifact
        loaded_artifact = await service.load_artifact(
            app_name="my_app",
            user_id="user123",
            session_id="session456",
            filename="hello.txt"
        )
        
        if loaded_artifact and loaded_artifact.inline_data:
            print(f"Artifact content: {loaded_artifact.inline_data.data.decode('utf-8')}")
        
    finally:
        # Clean up
        await service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## Integration with Google ADK

The custom services can be used directly with Google ADK runners:

```python
from google.adk.runners import InMemoryRunner
from custom_adk_services.sessions import YamlFileSessionService
from custom_adk_services.artifacts import LocalFolderArtifactService

# Create custom services
session_service = YamlFileSessionService("./sessions")
artifact_service = LocalFolderArtifactService("./artifacts")

# Create a runner with our custom services
runner = InMemoryRunner(
    agent=your_agent,
    session_service=session_service,
    artifact_service=artifact_service
)
```

## Development

### Running Examples

```bash
# Run session service examples
uv run python examples/session_service_example.py

# Run artifact service examples
uv run python examples/artifact_service_example.py

# Run the Google ADK integration example
uv run python examples/google_adk_integration.py
```

### Testing

To run tests, you'll need to install the test dependencies:

```bash
uv add pytest pytest-asyncio
```

Then run:

```bash
uv run pytest tests/
```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.