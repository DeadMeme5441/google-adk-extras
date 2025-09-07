---
title: Artifacts (How‑To)
---

# Artifacts (How‑To)

Store and retrieve binary artifacts (with versioning).

## Local Folder

```python
from google_adk_extras.artifacts import LocalFolderArtifactService
from google.genai import types

svc = LocalFolderArtifactService("./artifacts")
await svc.initialize()

part = types.Part(inline_data=types.Blob(data=b"hello", mime_type="text/plain"))
v = await svc.save_artifact(app_name="my_app", user_id="u1", session_id="s1", filename="greeting", artifact=part)
loaded = await svc.load_artifact(app_name="my_app", user_id="u1", session_id="s1", filename="greeting", version=v)
```

## S3

```python
from google_adk_extras.artifacts import S3ArtifactService
svc = S3ArtifactService(bucket_name="my-bucket")
await svc.initialize()
```

Other backends: SQL, MongoDB.

Tips

- Local is great for dev; use S3/SQL/Mongo in production.
- Use `list_versions` to implement rollback flows.

