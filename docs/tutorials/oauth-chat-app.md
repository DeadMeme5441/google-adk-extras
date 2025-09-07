---
title: Tutorial — OAuth Chat App
---

# Tutorial: OAuth‑backed Chat App

Build a simple chat app using SQL sessions/memory and Google OAuth2 credentials. You’ll secure the app with OAuth, persist conversation state, and run the FastAPI server with hot reloading.

What you’ll build

- FastAPI app serving an ADK agent via `EnhancedRunner`
- SQL session/memory stores; artifacts stored locally
- Google OAuth2 credential service for login/auth

Prereqs

- Python 3.12+
- `pip install google-adk-extras uvicorn`
- Create an OAuth 2.0 Client ID (Google Cloud Console) and note `CLIENT_ID`, `CLIENT_SECRET`

Steps

1) Create a simple agent

```bash
mkdir -p agents/chat
cat > agents/chat/agent.json << 'JSON'
{
  "name": "chat",
  "model": "gemini-2.0-flash",
  "instructions": "You are a helpful assistant."
}
JSON
```

2) App with Google OAuth2 + SQL session/memory

```python
# app.py
from fastapi import FastAPI
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.credentials import GoogleOAuth2CredentialService

cred = GoogleOAuth2CredentialService(
    client_id="${GOOGLE_CLIENT_ID}",
    client_secret="${GOOGLE_CLIENT_SECRET}",
    scopes=["openid", "email", "profile"],
)

app: FastAPI = get_enhanced_fast_api_app(
    agents_dir="./agents",
    session_service_uri="sqlite:///./sessions.db",
    memory_service_uri="yaml://./memory",     # simple dev memory
    artifact_service_uri="local://./artifacts",
    credential_service=cred,
    allow_origins=["*"],
    web=True,
    reload_agents=True,
)
```

3) Export env and run

```bash
export GOOGLE_CLIENT_ID="...apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="..."
uvicorn app:app --reload --port 8000
```

4) Test

- Open `http://localhost:8000/docs` to view the FastAPI/ADK UI.
- Start a chat with the `chat` agent; sign in via OAuth when prompted.
- Confirm sessions are created in `sessions.db` and memory files under `./memory`.

Next

- Switch memory to Redis or SQL for production.
- Store artifacts in S3 or GCS.
- Add structured logging and Cloud Trace (`trace_to_cloud=True`).

Troubleshooting

- Callback mismatch: ensure redirect URIs are configured correctly for your OAuth client.
- 401/403: verify scopes and token audience; check JWT or provider claims.
- CORS: set `allow_origins` to your frontend origins.
