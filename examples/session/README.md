# Session Services Examples

This directory contains comprehensive examples for all session service implementations, demonstrating production-ready session management with multiple storage backends.

## Available Session Services

### 🗄️ SQL-Based Sessions
- **[`sql_session_example.py`](sql_session_example.py)** - SQLSessionService with SQLite
  - Database schema and migrations
  - Advanced querying and filtering
  - Connection pooling and optimization
  - Support for PostgreSQL, MySQL, SQL Server

### 🍃 MongoDB Sessions  
- **[`mongodb_session_example.py`](mongodb_session_example.py)** - MongoSessionService
  - Document-based storage with indexing
  - Advanced MongoDB queries and aggregation
  - GridFS for large session data
  - Replica set and clustering support

### ⚡ Redis Sessions
- **[`redis_session_example.py`](redis_session_example.py)** - RedisSessionService
  - High-performance in-memory storage
  - TTL (time-to-live) and automatic expiration
  - Redis Streams for session events
  - Clustering and sentinel support

### 📄 YAML File Sessions
- **[`yaml_session_example.py`](yaml_session_example.py)** - YamlFileSessionService
  - Human-readable session storage
  - Perfect for development and debugging
  - Git-friendly configuration format
  - Automatic file organization

## Features Demonstrated

Each example showcases:

### Core Session Operations
- **Session Creation**: Creating new sessions with metadata
- **Session Retrieval**: Finding sessions by ID, user, or app
- **Session Updates**: Modifying session state and metadata
- **Event Management**: Adding events to sessions
- **Session Listing**: Querying sessions with filters

### Advanced Features
- **Async Operations**: Full async/await support for high performance
- **Connection Management**: Proper initialization and cleanup
- **Error Handling**: Graceful handling of service failures
- **Configuration**: Environment-based configuration patterns
- **Integration**: Working with Google ADK agents and runners

### Production Patterns
- **Health Checks**: Service availability monitoring
- **Logging**: Structured logging with correlation IDs
- **Security**: Secure session data handling
- **Performance**: Optimization techniques and best practices

## Requirements

- **Python 3.10+**
- **Google ADK**: `pip install google-adk`
- **This Package**: `pip install google-adk-extras`

### External Services (Optional)

Examples gracefully handle missing services:

- **MongoDB Example**: `docker run -d --name mongo -p 27017:27017 mongo`
- **Redis Example**: `docker run -d --name redis -p 6379:6379 redis`

## Running Examples

### Quick Start

```bash
cd /path/to/google-adk-extras

# SQL Session (always available)
uv run python examples/session/sql_session_example.py

# YAML Session (always available)  
uv run python examples/session/yaml_session_example.py

# MongoDB Session (requires MongoDB)
docker run -d --name mongo -p 27017:27017 mongo
uv run python examples/session/mongodb_session_example.py

# Redis Session (requires Redis)
docker run -d --name redis -p 6379:6379 redis
uv run python examples/session/redis_session_example.py
```

### Production Configuration Examples

#### SQL with PostgreSQL
```python
from google_adk_extras.sessions import SQLSessionService

# Production PostgreSQL setup
session_service = SQLSessionService(
    connection_string="postgresql://user:password@localhost/sessions",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
await session_service.initialize()
```

#### MongoDB with Authentication
```python
from google_adk_extras.sessions import MongoSessionService

# Production MongoDB with auth
session_service = MongoSessionService(
    connection_string="mongodb://user:password@localhost:27017/sessions?authSource=admin",
    database_name="sessions",
    collection_name="user_sessions"
)
await session_service.initialize()
```

#### Redis with Clustering
```python
from google_adk_extras.sessions import RedisSessionService

# Redis cluster setup
session_service = RedisSessionService(
    host="redis-cluster-endpoint",
    port=6379,
    password="your-redis-password",
    decode_responses=True,
    health_check_interval=30
)
await session_service.initialize()
```

## Integration Examples

### With Google ADK Runners

```python
from google.adk import Agent, Runner
from google_adk_extras.sessions import SQLSessionService

# Create session service
session_service = SQLSessionService("postgresql://localhost/sessions")
await session_service.initialize()

# Create agent and runner
agent = Agent(name="assistant", model="gemini-2.0-flash")
runner = Runner(
    agent=agent,
    session_service=session_service,
    app_name="my_app"
)

# Use with persistent sessions
result = await runner.run(
    "Hello, remember my name is Alice",
    user_id="user_123"
)
```

### With Enhanced Configuration

```python
from google_adk_extras.sessions import SQLSessionService
from google_adk_extras.configuration import ConfigurationSystem

# Load configuration
config_system = ConfigurationSystem()
config = await config_system.load_config("session_config.yaml")

# Create service from config
session_service = SQLSessionService(
    connection_string=config["database"]["url"],
    pool_size=config["database"]["pool_size"]
)
await session_service.initialize()
```

## Performance Benchmarks

Each example includes performance testing:

```python
import time
import asyncio

async def benchmark_session_service(service, num_operations=1000):
    """Benchmark session operations"""
    
    # Create sessions
    start_time = time.time()
    sessions = []
    for i in range(num_operations):
        session = await service.create_session(
            app_name="benchmark",
            user_id=f"user_{i}",
            state={"test": True}
        )
        sessions.append(session)
    
    create_time = time.time() - start_time
    print(f"Created {num_operations} sessions in {create_time:.2f}s")
    
    # Retrieve sessions
    start_time = time.time()
    for session in sessions:
        retrieved = await service.get_session(session.id)
    
    retrieve_time = time.time() - start_time
    print(f"Retrieved {num_operations} sessions in {retrieve_time:.2f}s")
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```python
   # Check connection string format
   # PostgreSQL: postgresql://user:pass@host:port/db
   # MySQL: mysql://user:pass@host:port/db
   # SQLite: sqlite:///path/to/file.db
   ```

2. **MongoDB Connection Issues**
   ```bash
   # Check MongoDB is running
   docker ps | grep mongo
   
   # Check connection
   mongo --eval "db.runCommand('ping')"
   ```

3. **Redis Connection Issues**
   ```bash
   # Check Redis is running
   redis-cli ping
   
   # Check port availability
   telnet localhost 6379
   ```

### Debug Mode

Enable detailed logging in any example:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Performance Tuning

- **SQL**: Use connection pooling, appropriate indexes
- **MongoDB**: Create indexes on frequently queried fields
- **Redis**: Use appropriate data structures and expiration policies
- **YAML**: Keep file sizes reasonable, use appropriate directory structure