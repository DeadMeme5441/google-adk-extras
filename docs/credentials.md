# Credentials

Provide auth to tools and agents using credential services.

## OAuth2
- `GoogleOAuth2CredentialService`
- `GitHubOAuth2CredentialService`
- `MicrosoftOAuth2CredentialService`
- `XOAuth2CredentialService`

```python
from google_adk_extras.credentials import GoogleOAuth2CredentialService

cred = GoogleOAuth2CredentialService(
    client_id="...",
    client_secret="...",
    scopes=["openid", "email", "profile"],
)

app = AdkBuilder().with_credential_service(cred).build_fastapi_app()
```

## JWT
- `JWTCredentialService` (requires `PyJWT` via extra `[jwt]`).

## HTTP Basic
- `HTTPBasicAuthCredentialService` and multi‑user variant.

Notes
- You can also configure via URIs (see URIs page).
- Credential storage defaults to ADK’s session/in‑memory stores.
