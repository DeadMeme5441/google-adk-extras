# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository provides custom implementations of Google ADK services (Session, Artifact, Memory) with multiple storage backends including SQL databases, MongoDB, Redis, S3, and YAML files. It extends the Google ADK framework with practical storage solutions for production applications.

## Architecture

The codebase follows a plugin-style architecture:

- **Base Classes**: Abstract base classes in `base_custom_*_service.py` define common patterns and initialization handling
- **Service Implementations**: Concrete implementations for different storage backends (SQL, MongoDB, Redis, S3, YAML)
- **Three Service Categories**:
  - **Sessions** (`src/google_adk_extras/sessions/`): Manage user sessions and state
  - **Artifacts** (`src/google_adk_extras/artifacts/`): Store and retrieve binary data/files
  - **Memory** (`src/google_adk_extras/memory/`): Handle conversational memory and search

All services follow async patterns and require explicit `initialize()` calls before use. The base classes handle initialization state tracking to prevent double initialization.

## Development Commands

### Installation and Setup
```bash
# Install dependencies with uv (recommended)
uv sync

# Or install with pip in development mode
pip install -e .
```

### Testing
```bash
# Run all tests (comprehensive test runner)
python tests/run_all_tests.py

# Run specific test categories with pytest
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests only  
uv run pytest tests/e2e/          # End-to-end tests only

# Run all tests with pytest
uv run pytest tests/

# Run single test file
uv run pytest tests/unit/test_session_services.py
```

The test suite includes:
- Unit tests for individual service functionality
- Integration tests for service interactions
- E2E tests for real-world scenarios
- Legacy integration tests (separate scripts)

### Key Test Markers
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests

## Project Structure

Each service type (sessions, artifacts, memory) follows the same pattern:
- Base abstract class with common initialization logic
- Multiple concrete implementations for different storage backends
- Comprehensive test coverage across unit/integration/e2e levels
- Example usage in `examples/` directory

Storage backends consistently supported across services:
- SQL (via SQLAlchemy) - supports SQLite, PostgreSQL, MySQL, etc.
- MongoDB (via PyMongo)
- Redis (for sessions and memory only)
- Local filesystem (YAML files, local folders for artifacts)
- AWS S3 (for artifacts only)

All services are async and require explicit initialization before use.