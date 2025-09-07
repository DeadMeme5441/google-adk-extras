---
title: Credentials (How‑To)
---

# Credentials (How‑To)

Use OAuth2 providers, JWT, or HTTP Basic with ADK. These services plug into `EnhancedRunner` and the enhanced FastAPI app to secure routes and inject credentials during tool/agent operations.

## Google OAuth2

```python
from google_adk_extras.credentials import GoogleOAuth2CredentialService

cred = GoogleOAuth2CredentialService(
    client_id="...apps.googleusercontent.com",
    client_secret="...",
    scopes=["openid", "email", "profile"],
)
await cred.initialize()  # validates configuration and sets up flows

# Use with FastAPI app
from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
app = get_enhanced_fast_api_app(agents_dir="./agents", credential_service=cred)
```

## JWT

```python
from google_adk_extras.credentials import JWTCredentialService
jwt = JWTCredentialService(secret="secret", issuer="my-app", audience="api.example.com", expiration_minutes=60)
await jwt.initialize()

# Generate token for a user/session
token = await jwt.generate_token({"user_id": "123", "role": "admin"})

# Validate token (e.g., in a custom route)
claims = await jwt.get_token_info(token)  # minimal info without full verification
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
- JWT: use strong secrets/keys, set issuer/audience/expiry.

URIs (AdkBuilder)

```python
from google_adk_extras import AdkBuilder

app = (
    AdkBuilder()
    .with_agents_dir("./agents")
    # Google OAuth2
    .with_credential_service_uri("oauth2-google://CLIENT_ID:CLIENT_SECRET@scopes=openid,email,profile")
    .build_fastapi_app()
)
```

Other providers

- GitHub OAuth2: `oauth2-github://client_id:secret@scopes=user,repo`
- Microsoft OAuth2: `oauth2-microsoft://tenant-id/client_id:secret@scopes=User.Read` (tenant required)
- X OAuth2: `oauth2-x://client_id:secret@scopes=tweet.read,users.read`
- JWT: `jwt://secret@algorithm=HS256&issuer=my-app&audience=api.example.com&expiration_minutes=60`
- Basic: `basic-auth://username:password@realm=My%20API`

Redirect URIs

- For OAuth2 providers, register redirect/callback URIs in the provider console.
- If running locally with ADK’s dev UI, use `http://localhost:8000/docs` or your app’s callback endpoint as configured by your integration.
