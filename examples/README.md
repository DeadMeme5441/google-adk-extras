# Google ADK Extras Examples

This directory contains comprehensive examples demonstrating all the powerful features of Google ADK Extras.

## Directory Structure

- [`session/`](session/) - Enhanced session services with multiple storage backends
- [`artifact/`](artifact/) - Artifact services for file and data storage
- [`memory/`](memory/) - Memory services for conversational context and search
- [`credentials/`](credentials/) - OAuth2 providers and authentication services
- [`configuration/`](configuration/) - Configuration system examples (Coming Soon)
- [`registry/`](registry/) - Agent and tool registry examples (Coming Soon)
- [`composition/`](composition/) - Agent composition and workflow examples (Coming Soon)

## What You'll Learn

### Core Services
- **Session Management**: Persistent session storage across SQL, MongoDB, Redis, and YAML
- **Artifact Storage**: File and binary data management with local, S3, and database backends
- **Memory Systems**: Conversational memory with search capabilities
- **Credential Services**: OAuth2 flows for Google, GitHub, Microsoft, X and token management

### Advanced Features  
- **Configuration Architecture**: YAML-driven configuration with environment interpolation
- **Registry Infrastructure**: Hot-swappable agents and tools with health monitoring
- **Agent Composition**: Multi-agent workflows and execution strategies
- **Enhanced Runners**: Production-ready runners with monitoring and error handling

## Requirements

- **Python 3.10+**
- **Google ADK**: `pip install google-adk`
- **This Package**: `pip install google-adk-extras`
- **UV Package Manager** (recommended): `pip install uv`

### External Service Requirements

Some examples require external services (all examples gracefully handle missing services):

- **MongoDB Examples**: Running MongoDB instance (`docker run -d -p 27017:27017 mongo`)
- **Redis Examples**: Running Redis instance (`docker run -d -p 6379:6379 redis`)
- **S3 Examples**: AWS credentials configured (`aws configure` or environment variables)
- **OAuth2 Examples**: Application credentials from respective providers

## Running Examples

### Quick Start

```bash
cd /path/to/google-adk-extras

# Run session examples
uv run python examples/session/sql_session_example.py
uv run python examples/session/mongodb_session_example.py
uv run python examples/session/redis_session_example.py
uv run python examples/session/yaml_session_example.py

# Run artifact examples
uv run python examples/artifact/sql_artifact_example.py
uv run python examples/artifact/local_folder_artifact_example.py
uv run python examples/artifact/s3_artifact_example.py

# Run memory examples
uv run python examples/memory/sql_memory_example.py
uv run python examples/memory/redis_memory_example.py

# Run credential examples (requires setup)
uv run python examples/credentials/google_oauth2_example.py
uv run python examples/credentials/jwt_credential_example.py
```

### With Docker Services

For MongoDB and Redis examples:

```bash
# Start services
docker run -d --name mongo -p 27017:27017 mongo
docker run -d --name redis -p 6379:6379 redis

# Run examples
uv run python examples/session/mongodb_session_example.py
uv run python examples/memory/redis_memory_example.py

# Cleanup
docker rm -f mongo redis
```

## Service Coverage

### 🗄️ Session Services
- **SQLSessionService**: SQLite, PostgreSQL, MySQL, SQL Server with advanced querying
- **MongoSessionService**: MongoDB with document-based storage and indexing
- **RedisSessionService**: High-performance Redis with TTL and clustering support
- **YamlFileSessionService**: Human-readable YAML storage for development

### 📁 Artifact Services
- **SQLArtifactService**: Database storage with metadata and versioning
- **MongoArtifactService**: GridFS support for large files and binary data
- **LocalFolderArtifactService**: Organized local filesystem with metadata
- **S3ArtifactService**: AWS S3 and compatible services (MinIO, DigitalOcean Spaces)

### 🧠 Memory Services
- **SQLMemoryService**: Persistent memory with SQL-based full-text search
- **MongoMemoryService**: Document-based memory with MongoDB's powerful query engine
- **RedisMemoryService**: Fast in-memory storage with Redis search capabilities
- **YamlFileMemoryService**: File-based memory for development and debugging

### 🔐 Credential Services
- **GoogleOAuth2**: Google APIs (Calendar, Gmail, Drive, Sheets, etc.)
- **GitHubOAuth2**: GitHub API (repositories, users, organizations, actions)
- **MicrosoftOAuth2**: Microsoft Graph (Outlook, Teams, OneDrive, SharePoint)
- **XOAuth2**: X (Twitter) API v2 (tweets, users, spaces, direct messages)
- **JWTCredentialService**: Token generation, validation, and claims management
- **HTTPBasicAuthCredentialService**: Username/password authentication

## Example Features

Each example demonstrates:

### Basic Operations
- **Service Initialization**: Proper setup and configuration
- **CRUD Operations**: Create, read, update, delete operations
- **Error Handling**: Graceful error handling and recovery
- **Resource Management**: Proper cleanup and resource disposal

### Advanced Features
- **Async/Await Patterns**: Modern Python async programming
- **Connection Management**: Connection pooling and optimization
- **Configuration**: Environment-based configuration
- **Integration**: Working with Google ADK agents and runners
- **Testing**: Unit and integration test patterns

### Production Patterns
- **Health Checks**: Service health monitoring
- **Logging**: Structured logging and debugging
- **Security**: Secure credential handling
- **Performance**: Optimization techniques and best practices

## Interactive Examples

Some examples include interactive components:

- **OAuth2 Examples**: Web-based authentication flows
- **Configuration Examples**: Interactive configuration builders
- **Agent Examples**: Chat interfaces with different storage backends
- **Registry Examples**: Dynamic agent loading and management

## Example Dependencies

Examples are designed to be self-contained with minimal dependencies:

```python
# Core dependencies (always available)
import asyncio
import os
import tempfile
import logging

# Google ADK (required)
from google.adk import Agent, Runner

# This package
from google_adk_extras.sessions import SQLSessionService
from google_adk_extras.credentials import GoogleOAuth2CredentialService

# Optional dependencies (gracefully handled)
try:
    import pymongo  # MongoDB examples
except ImportError:
    pymongo = None

try:
    import redis  # Redis examples
except ImportError:
    redis = None
```

## Troubleshooting

### Common Issues

1. **Service Connection Failures**: Examples gracefully skip unavailable services
2. **Credential Issues**: Check environment variables and service setup
3. **Permission Errors**: Ensure proper file/directory permissions
4. **Port Conflicts**: Check if ports 27017 (MongoDB) or 6379 (Redis) are in use

### Debug Mode

Enable debug logging in any example:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

- **Documentation**: Check the README in each example directory
- **Source Code**: Examples include detailed comments and docstrings
- **Issues**: Report problems on GitHub Issues
- **Discussions**: Ask questions on GitHub Discussions