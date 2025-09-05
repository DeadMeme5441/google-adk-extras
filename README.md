# Custom ADK Session Services

This package provides custom implementations of Google ADK's `BaseSessionService` for various storage backends.

## Available Session Services

### 1. SQLSessionService
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

### 2. MongoSessionService
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

### 3. RedisSessionService
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

### 4. YamlFileSessionService
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

## Installation

```bash
# First install Google ADK
pip install google-adk

# For all services
pip install sqlalchemy pymongo redis PyYAML

# For specific services only
pip install sqlalchemy  # For SQLSessionService only
pip install pymongo     # For MongoSessionService only
pip install redis       # For RedisSessionService only
pip install PyYAML      # For YamlFileSessionService only
```

## Usage Example

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

## Integration with Google ADK

The custom session services can be used directly with Google ADK runners:

```python
from google.adk.runners import InMemoryRunner
from custom_adk_services.sessions import YamlFileSessionService

# Create a custom session service
session_service = YamlFileSessionService("./sessions")

# Create a runner with our custom session service
runner = InMemoryRunner(
    agent=your_agent,
    session_service=session_service
)
```

## Development

### Running Examples

```bash
# Run the simple test
uv run python examples/test_session_service.py

# Run the comprehensive test
uv run python tests/test_session_services.py

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