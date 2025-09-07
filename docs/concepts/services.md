---
title: Services
---

# Services

Production-ready service implementations for sessions, memory, and artifacts that align with ADK’s core concepts: Session, State, and Memory. Use these to replace ADK’s in‑memory defaults with persistent, scalable backends.

## Sessions

Backends: SQL (SQLAlchemy), MongoDB, Redis, YAML files, In‑memory.

Common async API:

- `initialize()` — one‑time startup hook
- `create_session(app_name, user_id, ...)`
- `get_session(app_name, user_id, session_id, config=...)` (supports filtering events)
- `list_sessions(app_name, user_id, limit, offset)`
- `append_event(app_name, user_id, session_id, event)`
- `delete_session(app_name, user_id, session_id)`

Example (SQL):

```python
from google_adk_extras.sessions import SQLSessionService
svc = SQLSessionService("sqlite:///sessions.db")
await svc.initialize()
```

## Memory

Backends: SQL (text indexing), MongoDB, Redis, YAML files, In‑memory.

When an agent finishes, you may upsert facts into Memory and later `search_memory(...)` across conversations.

Example (SQL):

```python
from google_adk_extras.memory import SQLMemoryService
mem = SQLMemoryService("sqlite:///memory.db")
await mem.initialize()
```

Search supports simple OR‑term matching across extracted text content. For high‑recall scenarios, prefer SQL/Mongo backends; Redis favors speed.

## Artifacts

Backends: Local folder (versioned), S3 (+ compatible), SQL, MongoDB, In‑memory.

Artifacts store binary blobs emitted during runs (inputs, outputs, logs). Implementations support versioning and metadata.

Example (local):

```python
from google_adk_extras.artifacts import LocalFolderArtifactService
art = LocalFolderArtifactService("./artifacts")
await art.initialize()
```

## Credentials

Providers: Google/GitHub/Microsoft/X (OAuth2), JWT, HTTP Basic. These integrate with runners and the enhanced FastAPI app to secure endpoints and attach auth to downstream tools.

Example (JWT):

```python
from google_adk_extras.credentials import JWTCredentialService
jwt = JWTCredentialService(secret="your-secret")
await jwt.initialize()
```

Choosing backends

- Dev: YAML/Local/SQLite for simplicity and portability
- Prod: Postgres/MySQL for sessions/memory, Redis for speed‑critical paths, S3 for artifacts
- Cloud alignment: pick managed equivalents (Cloud SQL, MemoryStore/Redis, S3/GCS)

Operational tips

- Always `await initialize()` once per process
- Configure DB pool sizes; run migrations where applicable
- Keep artifact IO off hot paths; store references in sessions instead of large blobs
