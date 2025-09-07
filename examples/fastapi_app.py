"""Minimal FastAPI app using AdkBuilder.

Run:
  uvicorn examples.fastapi_app:app --reload

Requires (uv):
  uv pip install google-adk-extras[sql,yaml,web]
"""

from google_adk_extras import AdkBuilder


app = (
    AdkBuilder()
    # Use either on-disk agents...
    .with_agents_dir("./agents")
    # ...or register programmatic agents via CustomAgentLoader (see custom_loader.py)

    # Durable services
    .with_session_service("sqlite:///./sessions.db")
    .with_artifact_service("local://./artifacts")
    .with_memory_service("yaml://./memory")

    # Optional dev UI and hot reload (if ADK web assets available)
    .with_web_ui(True)
    .with_agent_reload(True)
    .build_fastapi_app()
)
