"""SQL-backed SessionService via builder URI.

Requires (uv): uv pip install google-adk-extras[sql]
"""

from google_adk_extras import AdkBuilder


builder = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
)

app = builder.build_fastapi_app()
