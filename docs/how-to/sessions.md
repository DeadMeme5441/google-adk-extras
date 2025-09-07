---
title: Sessions (How‑To)
---

# Sessions (How‑To)

Configure and use session storage backends.

## SQL (SQLite/Postgres/MySQL)

```python
from google_adk_extras.sessions import SQLSessionService
svc = SQLSessionService("sqlite:///sessions.db")
await svc.initialize()
session = await svc.create_session(app_name="my_app", user_id="u1")
```

## Redis

```python
from google_adk_extras.sessions import RedisSessionService
svc = RedisSessionService("redis://localhost:6379")
await svc.initialize()
```

## MongoDB

```python
from google_adk_extras.sessions import MongoSessionService
svc = MongoSessionService("mongodb://localhost:27017/sessions")
await svc.initialize()
```

## YAML Files (dev)

```python
from google_adk_extras.sessions import YamlFileSessionService
svc = YamlFileSessionService(base_directory="./sessions")
await svc.initialize()
```

Tips

- Always `await initialize()` once per process.
- For SQL, prefer pooled engines in production databases.
- Use `GetSessionConfig` to filter events on read if needed.

