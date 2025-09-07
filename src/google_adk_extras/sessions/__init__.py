"""Custom session service implementations for Google ADK.

Optional backends are imported lazily based on installed dependencies.
"""

try:
    from .sql_session_service import SQLSessionService  # type: ignore
except Exception:
    SQLSessionService = None  # type: ignore

try:
    from .mongo_session_service import MongoSessionService  # type: ignore
except Exception:
    MongoSessionService = None  # type: ignore

try:
    from .redis_session_service import RedisSessionService  # type: ignore
except Exception:
    RedisSessionService = None  # type: ignore

try:
    from .yaml_file_session_service import YamlFileSessionService  # type: ignore
except Exception:
    YamlFileSessionService = None  # type: ignore

__all__ = []
for _name in ("SQLSessionService", "MongoSessionService", "RedisSessionService", "YamlFileSessionService"):
    if globals().get(_name) is not None:
        __all__.append(_name)
