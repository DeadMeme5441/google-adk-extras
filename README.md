# google-adk-extras

[![PyPI](https://img.shields.io/pypi/v/google-adk-extras?label=PyPI)](https://pypi.org/project/google-adk-extras/)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)
[![Docs](https://img.shields.io/badge/docs-site-brightgreen)](https://deadmeme5441.github.io/google-adk-extras/)
[![Docs Build](https://github.com/DeadMeme5441/google-adk-extras/actions/workflows/docs.yml/badge.svg)](https://github.com/DeadMeme5441/google-adk-extras/actions/workflows/docs.yml)

Production-ready extensions for Google ADK (Agent Development Kit). This library adds durable service backends (sessions, artifacts, memory) and clean FastAPI wiring (with optional streaming) so you can run ADK agents with real storage.

What this is not: a fork of ADK. It builds on ADK’s core runtime, agents, tools and callbacks, and drops in where ADK expects services and a web server.


## Why it exists

ADK provides the core primitives (Runner, Session/State, MemoryService, ArtifactService, CredentialService, Agents/Tools, callbacks, Dev UI, and deployment paths). See the official ADK docs for concepts and APIs.

This package focuses on a few gaps common in real apps:
- Durable storage backends beyond in‑memory defaults
- FastAPI integration with optional streaming (SSE/WS)


## Features

- Session services: SQL (SQLite/Postgres/MySQL), MongoDB, Redis, YAML files
- Artifact services: Local folder (versioned), S3‑compatible, SQL, MongoDB
- Memory services: SQL, MongoDB, Redis, YAML files (term search over text parts)
- Enhanced FastAPI wiring for ADK apps (with optional streaming)
- Fluent builder (`AdkBuilder`) to assemble a FastAPI app or a Runner
 - A2A helpers for exposing/consuming agents (see below)

Note on Runner: `EnhancedRunner` is a thin subclass of ADK’s `Runner` for compatibility with the enhanced web server; it does not change behavior.


## Install

Requirements: Python 3.12+, google-adk.

Using uv:

```bash
# create a venv (optional)
uv venv && source .venv/bin/activate
# install the package
uv pip install google-adk-extras
```

If you plan to use specific backends, also install their clients (examples):
- SQL: `uv pip install sqlalchemy`
- MongoDB: `uv pip install pymongo`
- Redis: `uv pip install redis`
- S3: `uv pip install boto3`
  
Note on credentials (0.3.0): Outbound credentials for tools remain ADK’s concern (use ADK’s BaseCredentialService). Inbound API authentication is now available as an optional FastAPI layer in this package (see Auth below). You can run fully open (no auth) or enable API Key, Basic, or JWT (including first‑party issuance backed by SQL).


## Quickstart (FastAPI)

Use the fluent builder to wire services. Then run with uvicorn.

```python
# app.py
from google_adk_extras import AdkBuilder
from google_adk_extras.auth import AuthConfig, JwtIssuerConfig, JwtValidatorConfig

app = (
    AdkBuilder()
    .with_agents_dir("./agents")                          # ADK agents on disk
    .with_session_service("sqlite:///./sessions.db")      # or: mongodb://, redis://, yaml://
    .with_artifact_service("local://./artifacts")         # or: s3://bucket, mongodb://, sql://
    .with_memory_service("yaml://./memory")               # or: redis://, mongodb://, sql://
    # credentials: rely on ADK defaults or pass an ADK BaseCredentialService if needed
    .with_web_ui(True)     # serve ADK’s dev UI if assets available
    .with_agent_reload(True)
    .build_fastapi_app()
)
```

Run:

```bash
uvicorn app:app --reload
```

If you don’t keep agents on disk, register them programmatically and use a custom loader (see below).


## Auth (optional)

Auth is entirely optional. By default, all endpoints are open (no auth). To enable protection, pass `auth_config` into `get_enhanced_fast_api_app` via the builder or directly.

Supported inbound methods:
- API Key: `X-API-Key: <key>` header (or `?api_key=` query). Keys can be static via config, or issued/rotated via SQL‑backed endpoints.
- HTTP Basic: `Authorization: Basic base64(user:pass)` for quick human/internal testing. Can validate against in‑memory map or the SQL users table.
- Bearer JWT (validate): Accept JWTs from Google/Auth0/Okta/etc. via JWKS, or HS256 secret in dev. Enforces iss/aud/exp/nbf.
- Bearer JWT (issue): First‑party issuer with HS256, tokens minted from `/auth/token`, users stored in SQL (SQLite/Postgres/MySQL).

Per‑method gating:
- `allow_api_key`, `allow_basic`, `allow_bearer_jwt`, `allow_issuer_endpoints` (True/False to force, None=auto)
- `allow_query_api_key` (default True) to disable `?api_key=` usage
See docs/auth.md for examples and details. Also available: `GET /auth/me` to introspect the current identity.

Minimal enablement (JWT validate only):

```python
from google_adk_extras.auth import AuthConfig, JwtValidatorConfig

auth = AuthConfig(
    enabled=True,
    jwt_validator=JwtValidatorConfig(
        jwks_url="https://accounts.google.com/.well-known/openid-configuration",  # example
        issuer="https://accounts.google.com",
        audience="your-api-audience",
    ),
)

app = (
    AdkBuilder()
      .with_agents_dir("./agents")
      .build_fastapi_app()
)
```

First‑party issuer + validate (single shared HS256 secret) with SQL connector:

```python
from google_adk_extras.auth import AuthConfig, JwtIssuerConfig, JwtValidatorConfig

issuer = JwtIssuerConfig(
    enabled=True,
    issuer="https://local-issuer",
    audience="adk-api",
    algorithm="HS256",
    hs256_secret="topsecret",
    database_url="sqlite:///./auth.db",  # also supports Postgres/MySQL
)
validator = JwtValidatorConfig(
    issuer=issuer.issuer,
    audience=issuer.audience,
    hs256_secret=issuer.hs256_secret,
)

auth = AuthConfig(enabled=True, jwt_issuer=issuer, jwt_validator=validator)

app = (
    AdkBuilder()
      .with_agents_dir("./agents")
      .build_fastapi_app()
)
```

Issuing and using tokens/keys at runtime:
- Register user: `POST /auth/register?username=alice&password=wonder`
- Token (password): `POST /auth/token?grant_type=password&username=alice&password=wonder`
- Refresh: `POST /auth/refresh?user_id=<uid>&refresh_token=<jti>`
- Create API key: `POST /auth/api-keys` (auth required) → returns `{ id, api_key }` (plaintext shown once)
- List keys: `GET /auth/api-keys` (auth required)
- Revoke key: `DELETE /auth/api-keys/{id}` (auth required)
- Use API key: add `X-API-Key: <api_key>` to any protected route (keys currently allow full access)

Protected routes include `/run`, `/run_sse`, all `/apps/...` session/artifact/eval endpoints, `/debug/*`, `/builder/*`, and optionally `/list-apps` and `/apps/{app}/metrics-info`.


## Quickstart (Runner)

Create a Runner wired with your chosen backends. Use agent name (filesystem loader) or pass an agent instance.

```python
from google_adk_extras import AdkBuilder

runner = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
    .with_memory_service("redis://localhost:6379")
    .with_artifact_service("local://./artifacts")
    .build_runner("my_agent")
)

result = await runner.run("Hello there!")
```


## How this extends ADK (in practice)

ADK defines abstract service interfaces and a runner/web stack. This package provides drop‑in implementations and a small web‑server shim:

- Sessions
  - `SQLSessionService` — SQLAlchemy; JSON‑serialized state/events
  - `MongoSessionService` — PyMongo; per‑session doc, indexed by app/user/id
  - `RedisSessionService` — hashes per session + user set; JSON state/events
- `YamlFileSessionService` — `base/app/user/{session_id}.yaml`

### A2A helpers (new)

Two light-weight helpers wrap ADK’s A2A capabilities:

- `AdkBuilder.enable_a2a_for_registered_agents(enabled=True, mount_base="/a2a", card_factory=None)`
  - Expose programmatically registered agents (added via `with_agent_instance()` / `with_agents()`) over A2A without an `agents_dir`.
  - Optionally supply `card_factory(name, agent) -> dict` to build an Agent Card; otherwise a minimal card is used.

- `AdkBuilder.with_remote_a2a_agent(name, agent_card_url, description=None)`
  - Register a `RemoteA2aAgent` by agent card URL so your root agent can delegate to a remote agent.
  - Requires `google-adk[a2a]` installed.

Expose a programmatic agent via A2A:

```python
from google_adk_extras import AdkBuilder
from google.adk.agents import Agent

hello = Agent(model="gemini-2.0-flash", name="hello", instruction="You are helpful.")

app = (
    AdkBuilder()
      .with_agent_instance("hello", hello)
      .with_a2a_protocol(True)
      .enable_a2a_for_registered_agents()  # becomes available at /a2a/hello
      .build_fastapi_app()
)
```

Consume a remote A2A agent:

```python
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from google_adk_extras import AdkBuilder

card_url = f"http://remote-host:8001/a2a/prime{AGENT_CARD_WELL_KNOWN_PATH}"

app = (
    AdkBuilder()
      .with_remote_a2a_agent("prime_agent", card_url, description="Prime checker")
      # add your root agent via with_agent_instance(...)
      .build_fastapi_app()
)
```

- Artifacts
  - `LocalFolderArtifactService` — per‑artifact metadata JSON + versioned data files
  - `S3ArtifactService` — metadata JSON + versioned data objects in S3‑compatible storage
  - `SQLArtifactService` — blobs per version in SQL
  - `MongoArtifactService` — blobs per version in MongoDB

- Memory
  - `SQLMemoryService`, `MongoMemoryService`, `RedisMemoryService`, `YamlFileMemoryService`
  - Extracts text from `google.genai.types.Content`, tokenizes simple terms, and searches terms

- Credentials
  - OAuth2: Google, GitHub, Microsoft, X (Twitter)
  - Tokens: JWT (generate/verify/refresh‑aware), HTTP Basic (+ multi‑user variant)
  - Persist via ADK’s session/in‑memory credential stores

- FastAPI integration
  - `get_enhanced_fast_api_app(...)` accepts a provided credential service
  - `EnhancedAdkWebServer` returns `EnhancedRunner` and keeps ADK’s caching/cleanup
  - Prefer the fluent `AdkBuilder()` path for multi‑backend wiring in one place


## Agent loading options

- Directory loading (ADK default): `with_agents_dir("./agents")` and create `./agents/<app_name>/agent.json` (or your ADK agent files) per app.
- Programmatic agents: register instances and avoid a folder layout.

```python
from google_adk_extras import AdkBuilder
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google.adk.agents.base_agent import BaseAgent

loader = CustomAgentLoader()
loader.register_agent("my_app", BaseAgent(name="my_app"))  # replace with a real agent

app = (
    AdkBuilder()
    .with_agent_loader(loader)
    .with_session_service("sqlite:///./sessions.db")
    .build_fastapi_app()
)
```


<!-- Credential URI helpers removed. Use ADK’s BaseCredentialService directly if needed,
     and handle inbound API authentication at FastAPI level. -->


## Notes & limitations

- The runner in this package is intentionally thin. All agent logic, tools, callbacks, and evaluation remain ADK responsibilities.
- The repository currently ships only the pieces listed above; referenced registries or configuration subsystems are intentionally out of scope.
- Some direct FastAPI parameters (e.g., ADK’s special memory URIs) pass through for parity, but the fluent builder is the recommended path for the extended backends offered here.


## Docs

This repo ships a full MkDocs site in `docs/`.

Build locally with uv:

```bash
uv pip install .[docs]
uv run mkdocs serve
```

## Development

```bash
uv sync                 # or: pip install -e .
pytest -q               # run tests
```


## License

Apache 2.0 — see LICENSE.
