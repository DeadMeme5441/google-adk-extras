# Google ADK Custom Services

[![CI](https://github.com/DeadMeme5441/google-adk-extras/actions/workflows/ci.yml/badge.svg)](https://github.com/DeadMeme5441/google-adk-extras/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/google-adk-extras.svg)](https://badge.fury.io/py/google-adk-extras)

Custom implementations of Google ADK services (Session, Artifact, Memory) with multiple storage backends.

## Features

This package provides custom implementations for Google ADK services with various storage backends:

### Session Services
- **SQLSessionService**: Store sessions in SQL databases (SQLite, PostgreSQL, MySQL, etc.)
- **MongoSessionService**: Store sessions in MongoDB
- **RedisSessionService**: Store sessions in Redis
- **YamlFileSessionService**: Store sessions in YAML files

### Artifact Services
- **SQLArtifactService**: Store artifacts in SQL databases
- **MongoArtifactService**: Store artifacts in MongoDB
- **LocalFolderArtifactService**: Store artifacts in local file system
- **S3ArtifactService**: Store artifacts in AWS S3 or S3-compatible services

### Memory Services
- **SQLMemoryService**: Store memories in SQL databases
- **MongoMemoryService**: Store memories in MongoDB
- **RedisMemoryService**: Store memories in Redis
- **YamlFileMemoryService**: Store memories in YAML files

## Installation

```bash
pip install google-adk-extras
```

## Usage

### Session Services

```python
from google_adk_extras.sessions import SQLSessionService

# Initialize SQL session service
session_service = SQLSessionService("sqlite:///sessions.db")
await session_service.initialize()

# Create a session
session = await session_service.create_session(
    app_name="my_app",
    user_id="user_123",
    state={"theme": "dark"}
)
```

### Artifact Services

```python
from google_adk_extras.artifacts import LocalFolderArtifactService
from google.genai import types

# Initialize local folder artifact service
artifact_service = LocalFolderArtifactService("./artifacts")
await artifact_service.initialize()

# Save an artifact
text_blob = types.Blob(data=b"Hello, world!", mime_type="text/plain")
text_part = types.Part(inline_data=text_blob)
version = await artifact_service.save_artifact(
    app_name="my_app",
    user_id="user_123",
    session_id="session_456",
    filename="hello.txt",
    artifact=text_part
)
```

### Memory Services

```python
from google_adk_extras.memory import RedisMemoryService
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Initialize Redis memory service
memory_service = RedisMemoryService(host="localhost", port=6379)
await memory_service.initialize()

# Add a session to memory
session = Session(id="session_1", app_name="my_app", user_id="user_123", events=[])
await memory_service.add_session_to_memory(session)

# Search memory
response = await memory_service.search_memory(
    app_name="my_app",
    user_id="user_123",
    query="important information"
)
```

## Examples

See the [examples](examples/) directory for complete working examples of each service.

## Requirements

- Python 3.10+
- Google ADK
- Storage backend dependencies (installed automatically):
  - SQLAlchemy for SQL services
  - PyMongo for MongoDB services
  - redis-py for Redis services
  - PyYAML for YAML file services
  - boto3 for S3 services

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/DeadMeme5441/google-adk-extras.git
cd google-adk-extras

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run specific test suite
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/e2e/
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.