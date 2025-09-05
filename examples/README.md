# Google ADK Custom Services Examples

This directory contains end-to-end examples for all custom Google ADK services.

## Directory Structure

- [`session/`](session/) - Examples for custom session services
- [`artifact/`](artifact/) - Examples for custom artifact services
- [`memory/`](memory/) - Examples for custom memory services

## Overview

Each directory contains:

1. `example.py` - A comprehensive example demonstrating the service
2. `README.md` - Instructions for running the example

## Requirements

- Python 3.10+
- Google ADK installed
- UV package manager

Some examples require additional services:
- MongoDB examples need a running MongoDB instance
- Redis examples need a running Redis instance
- S3 examples need AWS credentials configured

## Running Examples

To run any example:

```bash
cd /path/to/google-adk-extras
uv run python examples/[service_type]/example.py
```

For example:
```bash
uv run python examples/session/example.py
uv run python examples/artifact/example.py
uv run python examples/memory/example.py
```

## Service Coverage

### Session Services
- SQLSessionService (SQLite, PostgreSQL, MySQL, etc.)
- MongoSessionService (MongoDB)
- RedisSessionService (Redis)
- YamlFileSessionService (File-based)

### Artifact Services
- SQLArtifactService (SQLite, PostgreSQL, MySQL, etc.)
- MongoArtifactService (MongoDB)
- LocalFolderArtifactService (File-based)
- S3ArtifactService (AWS S3 and S3-compatible services)

### Memory Services
- SQLMemoryService (SQLite, PostgreSQL, MySQL, etc.)
- MongoMemoryService (MongoDB)
- RedisMemoryService (Redis)
- YamlFileMemoryService (File-based)

## Notes

- Examples that require external services (MongoDB, Redis, S3) will gracefully skip if those services aren't available
- All examples use temporary files/databases where possible to avoid side effects
- Examples demonstrate both basic operations and integration with Google ADK runners