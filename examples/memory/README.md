# Memory Services Examples

This directory contains examples for all custom memory service implementations.

## Examples

- [`sql_memory_example.py`](sql_memory_example.py) - SQLMemoryService (SQLite)
- [`mongodb_memory_example.py`](mongodb_memory_example.py) - MongoMemoryService (MongoDB)
- [`redis_memory_example.py`](redis_memory_example.py) - RedisMemoryService (Redis)
- [`yaml_memory_example.py`](yaml_memory_example.py) - YamlFileMemoryService (File-based)

## Requirements

- Python 3.10+
- Google ADK installed
- For MongoDB example: Running MongoDB instance
- For Redis example: Running Redis instance

## Running Examples

To run any example:

```bash
cd /path/to/google-adk-extras
uv run python examples/memory/[example_name].py
```

For example:
```bash
uv run python examples/memory/sql_memory_example.py
uv run python examples/memory/mongodb_memory_example.py
uv run python examples/memory/redis_memory_example.py
uv run python examples/memory/yaml_memory_example.py
```

## Notes

- MongoDB and Redis examples will be skipped if their respective services aren't running
- All examples use temporary files/databases where possible to avoid side effects
- Examples demonstrate memory operations: add sessions, search for content
- Different search patterns are demonstrated