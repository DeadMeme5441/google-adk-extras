# Google ADK Extras

[![CI](https://github.com/DeadMeme5441/google-adk-extras/actions/workflows/ci.yml/badge.svg)](https://github.com/DeadMeme5441/google-adk-extras/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/google-adk-extras.svg)](https://badge.fury.io/py/google-adk-extras)

[Documentation](https://DeadMeme5441.github.io/google-adk-extras/) · [Examples](examples/)

A comprehensive extension library for Google ADK that provides production-ready implementations of custom services, enhanced runners, and a flexible configuration system.

## Overview

This package transforms Google ADK from a simple framework into a production-ready platform by providing:
- **Custom ADK Services** with multiple storage backends (SQL, MongoDB, Redis, S3, YAML)
- **Enhanced Registry Infrastructure** with agent and tool registries, hot-swapping capabilities
- **Credential Services** for OAuth2 providers (Google, GitHub, Microsoft, X) and authentication systems
- **Flexible Configuration Architecture** with automatic format detection and environment interpolation
- **Enhanced Web Server** with FastAPI integration and advanced features
  
Note: Agent composition remains available via ADK’s native sequential/parallel/loop agents.

## Features

### 🗄️ Enhanced ADK Services

#### Session Services
- **SQLSessionService**: Store sessions in SQL databases (SQLite, PostgreSQL, MySQL, etc.)
- **MongoSessionService**: Store sessions in MongoDB with advanced querying
- **RedisSessionService**: High-performance session storage in Redis
- **YamlFileSessionService**: Human-readable file-based session storage

#### Artifact Services
- **SQLArtifactService**: Store artifacts with metadata in SQL databases
- **MongoArtifactService**: MongoDB-backed artifact storage with GridFS support
- **LocalFolderArtifactService**: Organized local file system artifact storage
- **S3ArtifactService**: Scalable cloud storage with AWS S3 and S3-compatible services

#### Memory Services
- **SQLMemoryService**: Persistent memory with SQL-based search capabilities
- **MongoMemoryService**: Document-based memory with MongoDB's powerful query engine
- **RedisMemoryService**: Fast in-memory storage with Redis search capabilities
- **YamlFileMemoryService**: Human-readable memory storage for development

### 🔐 Credential Services
- **OAuth2 Providers**: Google, GitHub, Microsoft, X (Twitter) with automatic token refresh
- **JWT Token Service**: Token generation, validation, and management
- **HTTP Basic Auth**: Username/password authentication with secure storage
- **Credential Integration**: Seamless integration with ADK agents and runners

### 🏗️ Enhanced Registry Infrastructure
- **Agent Registry**: Hot-swappable agent management with health monitoring
- **Tool Registry**: Dynamic tool loading with dependency management and versioning
- **Event System**: Comprehensive event handling for registry operations
- **Health Monitoring**: Built-in health checks and status reporting

### ⚙️ Flexible Configuration Architecture
- **Multiple Format Support**: YAML, JSON, TOML, Environment Variables, Remote URLs
- **Environment Interpolation**: Multi-syntax support (shell, bash, python patterns)
- **Configuration Validation**: Schema validation with severity levels and suggestions
- **Automatic Format Detection**: Smart detection of configuration formats
- **Enhanced RunConfig**: YAML-driven configuration system extending ADK's RunConfig

### 🚀 Enhanced Web Server & FastAPI Integration
- **Enhanced ADK Web Server**: Extended web server with additional features
- **FastAPI Integration**: Full FastAPI compatibility with ADK agents
- **Custom Agent Loader**: Instance-based agent management
- **Advanced Routing**: Dynamic route registration and management

### 🤖 Enhanced Runners
- **Enhanced Runner**: Extended ADK runner with monitoring and error handling
- **YAML-Driven Systems**: Define runner behavior in configuration files

## Installation

```bash
# Install from PyPI
pip install google-adk-extras

# Install with specific backends (optional)
pip install google-adk-extras[mongodb]  # MongoDB support
pip install google-adk-extras[redis]    # Redis support
pip install google-adk-extras[s3]       # S3 support
pip install google-adk-extras[all]      # All backends

# Development installation
git clone https://github.com/DeadMeme5441/google-adk-extras.git
cd google-adk-extras
uv sync  # or pip install -e .
```

## Quick Start

### 1. Enhanced ADK Services

```python
from google_adk_extras.sessions import SQLSessionService
from google_adk_extras.artifacts import S3ArtifactService
from google_adk_extras.memory import RedisMemoryService

# Initialize services with different backends
session_service = SQLSessionService("postgresql://user:pass@localhost/sessions")
artifact_service = S3ArtifactService(bucket="my-artifacts", region="us-east-1")
memory_service = RedisMemoryService(host="localhost", port=6379)

# Initialize all services
await session_service.initialize()
await artifact_service.initialize()  
await memory_service.initialize()
```

### 2. Configuration System

```python
from google_adk_extras.configuration import ConfigurationSystem

# Automatic format detection and environment interpolation
config_system = ConfigurationSystem()

# Load from various sources
config = await config_system.load_config("config.yaml")  # YAML
config = await config_system.load_config("config.json")  # JSON
config = await config_system.load_config("CONFIG_ENV")   # Environment variable
config = await config_system.load_config("https://my-site.com/config.yaml")  # Remote

# Environment interpolation examples in YAML:
# database_url: ${DATABASE_URL}           # Shell style
# api_key: ${API_KEY:default-key}         # With default
# debug: ${{os.environ.get('DEBUG', 'false')}}  # Python expression
```

### 3. Enhanced Registry with Hot-Swapping

```python
from google_adk_extras.runners.registry import AgentRegistry, ToolRegistry

# Create registries
agent_registry = AgentRegistry()
tool_registry = ToolRegistry()

# Register agents and tools
await agent_registry.register_agent("chat-agent", my_chat_agent)
await tool_registry.register_tool("calculator", my_calculator_tool)

# Hot-swap agents (zero downtime)
await agent_registry.update_agent("chat-agent", improved_chat_agent)

# Health monitoring
health = await agent_registry.get_health_status()
print(f"Registry health: {health}")
```

### 4. Credential Services

```python
from google_adk_extras.credentials import GoogleOAuth2CredentialService, JWTCredentialService

# OAuth2 setup
credential_service = GoogleOAuth2CredentialService(
    client_id="your-client-id.apps.googleusercontent.com",
    client_secret="your-client-secret",
    scopes=["openid", "email", "calendar"]
)

# JWT token service
jwt_service = JWTCredentialService(secret="your-jwt-secret")
token = await jwt_service.generate_token({"user_id": "123", "role": "admin"})
```

### 5. Enhanced Runner

```python
from google_adk_extras.runners import EnhancedRunner

# Enhanced runner with monitoring
runner = EnhancedRunner(
    agent=my_agent,
    session_service=session_service,
    credential_service=credential_service,
    app_name="my_app"
)

result = await runner.run("Process this request")
```

### 6. YAML-Driven Configuration

```yaml
# config.yaml - Complete system configuration
agents:
  - name: "chat-agent"
    model: "gemini-2.0-flash"
    instructions: "You are a helpful assistant"
    tools: ["search", "calculator"]

services:
  session:
    type: "sql"
    connection_string: "${DATABASE_URL}"
  
  artifacts:
    type: "s3"
    bucket: "${S3_BUCKET}"
    region: "us-east-1"
    
  memory:
    type: "redis"
    host: "${REDIS_HOST:localhost}"
    port: 6379

credentials:
  google:
    client_id: "${GOOGLE_CLIENT_ID}"
    client_secret: "${GOOGLE_CLIENT_SECRET}"
    scopes: ["calendar", "email"]

runner:
  monitoring_enabled: true
  error_handling: "graceful"
  max_retries: 3
```

```python
# Load and run with YAML config
from google_adk_extras.runners.config import EnhancedRunConfig

config = await EnhancedRunConfig.from_yaml("config.yaml")
runner = await config.create_runner()
result = await runner.run("Hello, how can you help me?")
```

## Architecture

The codebase follows a plugin-style architecture with clear separation of concerns:

- **Base Classes**: Abstract base classes define common patterns and initialization handling
- **Service Implementations**: Concrete implementations for different storage backends
- **Configuration System**: Flexible configuration loading with validation and interpolation
- **Registry Infrastructure**: Dynamic component registration with health monitoring

All services follow async patterns and require explicit `initialize()` calls before use.

## Examples & Documentation

- [**Examples Directory**](examples/): Comprehensive examples for all services
- [**Session Examples**](examples/session/): All session service implementations
- [**Artifact Examples**](examples/artifact/): All artifact service implementations  
- [**Memory Examples**](examples/memory/): All memory service implementations
- [**Credential Examples**](examples/credentials/): OAuth2 and authentication examples

Each example includes:
- Complete working code
- Setup instructions
- Best practices
- Error handling patterns

## Requirements

- **Python 3.12+**
- **Google ADK** (`pip install google-adk`)

### Optional Dependencies (installed automatically with extras)

- **SQL Support**: SQLAlchemy, psycopg2 (PostgreSQL), mysqlclient (MySQL)
- **MongoDB Support**: PyMongo, motor
- **Redis Support**: redis-py, redis[hiredis]
- **S3 Support**: boto3, botocore
- **Configuration**: PyYAML, toml, aiohttp
- **Authentication**: PyJWT, cryptography

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/DeadMeme5441/google-adk-extras.git
cd google-adk-extras

# Install with uv (recommended)
uv sync

# Or install with pip in development mode
pip install -e .
```

### Running Tests

The project includes comprehensive testing with 592 tests covering unit, integration, and end-to-end scenarios.

```bash
# Run all tests (comprehensive test runner)
python tests/run_all_tests.py

# Run with pytest
uv run pytest tests/                    # All tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests only  
uv run pytest tests/e2e/               # End-to-end tests only

# Run specific test file
uv run pytest tests/unit/test_session_services.py

# Run with coverage
uv run pytest --cov=google_adk_extras tests/
```

### Test Categories

- **Unit Tests**: Individual service functionality
- **Integration Tests**: Service interactions and workflows
- **E2E Tests**: Real-world scenarios with external services
- **Legacy Tests**: Backward compatibility validation

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python tests/run_all_tests.py`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Performance & Scalability

- **Async/Await**: Full async support for high-performance applications
- **Connection Pooling**: Built-in connection pooling for all database backends
- **Caching**: Intelligent caching strategies for configuration and registry data
- **Hot-Swapping**: Zero-downtime agent and tool updates
- **Health Monitoring**: Built-in health checks and performance metrics

## Security

- **Credential Management**: Secure handling of OAuth2 tokens and API keys
- **Environment Isolation**: Safe environment variable interpolation
- **Validation**: Comprehensive input validation and sanitization
- **Token Refresh**: Automatic OAuth2 token refresh and rotation

## Production Deployment

The library is designed for production use with:
- Comprehensive error handling and recovery
- Monitoring and observability features
- Scalable storage backends
- Configuration validation
- Health check endpoints
- Performance optimization

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/DeadMeme5441/google-adk-extras/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DeadMeme5441/google-adk-extras/discussions)
- **Documentation**: See examples directory for detailed usage patterns
