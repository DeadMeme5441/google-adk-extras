---
title: Migrate from ADK Defaults
---

# Migrate from ADK Defaults

This guide maps ADK defaults to production‑ready choices in this library.

Services

- Sessions: In‑memory → `SQLSessionService` (`sqlite:///` locally; Postgres in prod), or `RedisSessionService` for speed.
- Memory: In‑memory → `SQLMemoryService`/`RedisMemoryService`/`MongoMemoryService` as needed.
- Artifacts: In‑memory → `LocalFolderArtifactService` (dev) or `S3ArtifactService` (prod).

Credentials

- None/in‑memory → provider OAuth2 (`GoogleOAuth2CredentialService`, `GitHubOAuth2CredentialService`, `MicrosoftOAuth2CredentialService`, `XOAuth2CredentialService`), or `JWTCredentialService` / `HTTPBasicAuthCredentialService`.

Runtime configuration

- ADK `RunConfig` only → add `EnhancedRunConfig` to set per‑tool timeouts, retries, and circuit breaker.

Server

- CLI: `adk web` or `adk api_server` → code: `get_enhanced_fast_api_app` or `AdkBuilder().build_fastapi_app()` to embed in your app stack.

URIs (quick reference)

- Sessions: `sqlite:///db.db`, `postgresql://...`, `redis://...`, `mongodb://...`, `yaml://...`
- Memory: same as sessions
- Artifacts: `local://./artifacts`, `s3://bucket`, `sqlite:///...`, `mongodb://...`
- Credentials: `oauth2-google://...`, `oauth2-github://...`, `oauth2-microsoft://tenant/client:secret@scopes=...`, `oauth2-x://...`, `jwt://secret@...`, `basic-auth://user:pass@realm=...`

See also

- ADK Get Started: https://raw.githubusercontent.com/google/adk-docs/main/docs/get-started/index.md
- ADK Sessions & Memory: https://raw.githubusercontent.com/google/adk-docs/main/docs/sessions/index.md
