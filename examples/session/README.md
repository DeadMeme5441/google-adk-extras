# Session Services Examples

This directory contains examples for all custom session service implementations.

## Examples

- [`sql_session_example.py`](sql_session_example.py) - SQLSessionService (SQLite)
- [`mongodb_session_example.py`](mongodb_session_example.py) - MongoSessionService (MongoDB)
- [`redis_session_example.py`](redis_session_example.py) - RedisSessionService (Redis)
- [`yaml_session_example.py`](yaml_session_example.py) - YamlFileSessionService (File-based)

## Requirements

- Python 3.10+
- Google ADK installed
- For MongoDB example: Running MongoDB instance
- For Redis example: Running Redis instance

## Running Examples

To run any example:

```bash
cd /path/to/google-adk-extras
uv run python examples/session/[example_name].py
```

For example:
```bash
uv run python examples/session/sql_session_example.py
uv run python examples/session/mongodb_session_example.py
uv run python examples/session/redis_session_example.py
uv run python examples/session/yaml_session_example.py
```

## Notes

- MongoDB and Redis examples will be skipped if their respective services aren't running
- All examples use temporary files/databases where possible to avoid side effects
- Examples demonstrate basic session operations: create, retrieve, list, add events