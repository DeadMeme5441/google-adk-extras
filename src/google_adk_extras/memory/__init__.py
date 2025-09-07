"""Custom ADK memory services package.

Optional backends are imported lazily based on installed dependencies.
"""

from .base_custom_memory_service import BaseCustomMemoryService

# Optional dependencies
try:
    from .sql_memory_service import SQLMemoryService  # type: ignore
except Exception:
    SQLMemoryService = None  # type: ignore

try:
    from .mongo_memory_service import MongoMemoryService  # type: ignore
except Exception:
    MongoMemoryService = None  # type: ignore

try:
    from .redis_memory_service import RedisMemoryService  # type: ignore
except Exception:
    RedisMemoryService = None  # type: ignore

try:
    from .yaml_file_memory_service import YamlFileMemoryService  # type: ignore
except Exception:
    YamlFileMemoryService = None  # type: ignore

__all__ = ["BaseCustomMemoryService"]
for _name in ("SQLMemoryService", "MongoMemoryService", "RedisMemoryService", "YamlFileMemoryService"):
    if globals().get(_name) is not None:
        __all__.append(_name)
