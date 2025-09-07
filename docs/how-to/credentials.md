---
title: Credentials (How‑To)
---

# Credentials (How‑To)

Use OAuth2 providers, JWT, or HTTP Basic with ADK.

## Google OAuth2

```python
from google_adk_extras.credentials import GoogleOAuth2CredentialService

cred = GoogleOAuth2CredentialService(
  client_id="...",
  client_secret="...",
  scopes=["openid", "email", "profile"]
)
await cred.initialize()
```

## JWT

```python
from google_adk_extras.credentials import JWTCredentialService
jwt = JWTCredentialService(secret="secret", issuer="my-app")
await jwt.initialize()
```

## HTTP Basic

```python
from google_adk_extras.credentials import HTTPBasicAuthCredentialService
basic = HTTPBasicAuthCredentialService(username="u", password="p", realm="API")
await basic.initialize()
```

Integrate with Runner or FastAPI by passing the `credential_service`.

Security

- Store secrets securely (env vars or secret manager).
- For OAuth2, configure allowed redirect URIs and rotate client secrets.

