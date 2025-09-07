---
title: Services
---

# Services

Production-ready service implementations for sessions, memory, and artifacts.

## Sessions

Backends: SQL (SQLAlchemy), MongoDB, Redis, YAML files, In-memory.

Common API (async): `initialize()`, `create_session`, `get_session`, `list_sessions`, `append_event`, `delete_session`.

Example (SQL):

```python
from google_adk_extras.sessions import SQLSessionService
svc = SQLSessionService("sqlite:///sessions.db")
await svc.initialize()
```

## Memory

Backends: SQL (indexing text content), MongoDB, Redis, YAML files, In-memory.

Example (SQL):

```python
from google_adk_extras.memory import SQLMemoryService
mem = SQLMemoryService("sqlite:///memory.db")
await mem.initialize()
```

Search supports simple OR-term matching across extracted text content.

## Artifacts

Backends: Local folder (versioned), S3 (+ compatible), SQL, MongoDB, In-memory.

Example (local):

```python
from google_adk_extras.artifacts import LocalFolderArtifactService
art = LocalFolderArtifactService("./artifacts")
await art.initialize()
```

## Credentials

Providers: Google/GitHub/Microsoft/X (OAuth2), JWT, HTTP Basic.

Example (JWT):

```python
from google_adk_extras.credentials import JWTCredentialService
jwt = JWTCredentialService(secret="your-secret")
await jwt.initialize()
```

Notes

- All custom services inherit base classes that ensure `initialize()` is called before use.
- Choose backends to match your environment (dev vs prod) and scale needs.

