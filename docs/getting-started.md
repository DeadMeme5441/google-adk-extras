# Getting Started

## Install

Requirements: Python 3.12+, `google-adk`.

- Core: `uv pip install google-adk-extras`
- Pick extras for your backends:
  - SQL: `uv pip install google-adk-extras[sql]`
  - MongoDB: `uv pip install google-adk-extras[mongodb]`
  - Redis: `uv pip install google-adk-extras[redis]`
  - YAML: `uv pip install google-adk-extras[yaml]`
  - S3: `uv pip install google-adk-extras[s3]`
  - JWT: `uv pip install google-adk-extras[jwt]`
  - Web server: `uv pip install google-adk-extras[web]`

## Minimal FastAPI App

```python
from google_adk_extras import AdkBuilder

app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
    .with_artifact_service("local://./artifacts")
    .with_memory_service("yaml://./memory")
    .with_web_ui(True)
    .with_agent_reload(True)
    .build_fastapi_app()
)
```

Run with: `uvicorn app:app --reload`.

## Minimal Runner

```python
runner = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
    .with_memory_service("yaml://./memory")
    .with_artifact_service("local://./artifacts")
    .build_runner("my_agent")
)
```

See Examples for complete scripts.
