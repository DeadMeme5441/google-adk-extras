"""Local folder ArtifactService via builder URI.

Stores artifacts under ./artifacts with metadata and versioning.
"""

from google_adk_extras import AdkBuilder


app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_artifact_service("local://./artifacts")
    .build_fastapi_app()
)

