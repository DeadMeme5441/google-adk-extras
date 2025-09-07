"""YAML-backed MemoryService via builder URI.

Requires (uv): uv pip install google-adk-extras[yaml]
"""

from google_adk_extras import AdkBuilder


app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_memory_service("yaml://./memory")
    .build_fastapi_app()
)
