# Durable Services

ADK defines service interfaces; this package provides drop‑in durable implementations.

## Sessions
- `SQLSessionService` — SQLAlchemy; JSON‑serialized state/events. URI: `sqlite:///...`, `postgresql://...`, `mysql://...`.
- `MongoSessionService` — Async PyMongo (no Motor). Per‑session doc in `sessions` + separate `events`, `app_states`, `user_states`. URI: `mongodb://host/db`.
- `RedisSessionService` — Hashes/sets per session/user. URI: `redis://host:6379`.
- `YamlFileSessionService` — Files under `base/app/user/{session_id}.yaml`. URI: `yaml://./path`.

Configure via builder:

```python
AdkBuilder().with_session_service("sqlite:///./sessions.db")
```

## Artifacts
- `LocalFolderArtifactService` — Metadata JSON + versioned data files. URI: `local://./artifacts`.
- `S3ArtifactService` — S3‑compatible buckets. URI: `s3://bucket`.
- `SQLArtifactService` — Blobs per version in SQL. URI like sessions.
- `MongoArtifactService` — Blobs in MongoDB. URI like sessions.

```python
AdkBuilder().with_artifact_service("local://./artifacts")
```

## Memory
- `SQLMemoryService`, `MongoMemoryService`, `RedisMemoryService`, `YamlFileMemoryService`
- Extracts text from `google.genai.types.Content` parts and indexes basic terms for search.

```python
AdkBuilder().with_memory_service("yaml://./memory")
```

Notes
- Use the matching install extras: `[sql]`, `[mongodb]`, `[redis]`, `[yaml]`, `[s3]`.
- For Mongo sessions, install `google-adk-extras[mongodb]` which brings `pymongo>=4.14` (async API).
- Service instances are also supported: `.with_session_service_instance(SQLSessionService(...))`.

## Auth
- Issuer endpoints and middleware can use an auth store for users/refresh tokens and API keys.
- Backends: SQL (`sqlite:///`, `postgresql://`, `mysql://`) or MongoDB (`mongodb://host/db`).
- Enable via `AuthConfig(jwt_issuer=JwtIssuerConfig(database_url=...))`.
