"""Google OAuth2 credential service example.

Requires (uv):
  uv pip install google-adk-extras[web]

Note: Provide valid client_id/client_secret and scopes for your app.
"""

from google_adk_extras import AdkBuilder
from google_adk_extras.credentials import GoogleOAuth2CredentialService


credential = GoogleOAuth2CredentialService(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    scopes=["openid", "email", "profile"],
)

app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    .with_session_service("sqlite:///./sessions.db")
    .with_artifact_service("local://./artifacts")
    .with_memory_service("yaml://./memory")
    .with_credential_service(credential)
    .build_fastapi_app()
)
