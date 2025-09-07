---
title: Tutorial — OAuth Chat App
---

# Tutorial: OAuth‑backed Chat App

Build a simple chat app using SQL sessions/memory and Google OAuth2 credentials.

What you’ll build

- FastAPI app serving an agent via EnhancedRunner
- SQL session/memory stores; artifacts to local
- Google OAuth2 credential service

Steps

1) Install deps and set env vars for Google OAuth2.
2) Create `agents/` with a simple agent.
3) Wire FastAPI via `get_enhanced_fast_api_app` and pass `GoogleOAuth2CredentialService`.
4) Run with Uvicorn and test the UI and auth flow.

Code

Refer to Quickstart (FastAPI) and Credentials How‑To for concrete snippets; join them in a single file and run `uvicorn`.

Next

- Persist artifacts to S3, add structured logging, deploy to cloud.

