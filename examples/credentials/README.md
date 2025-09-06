# Credential Service Examples

This directory contains examples of using the various credential services provided by google-adk-extras.

## Available Credential Services

### OAuth2 Services
- **[Google OAuth2](google_oauth2_example.py)** - Google APIs authentication (Calendar, Gmail, Drive, etc.)
- **[GitHub OAuth2](github_oauth2_example.py)** - GitHub API authentication (repositories, users, organizations)
- **[Microsoft OAuth2](microsoft_oauth2_example.py)** - Microsoft Graph API authentication (Outlook, Teams, OneDrive)
- **[X (Twitter) OAuth2](x_oauth2_example.py)** - X API v2 authentication (tweets, users, spaces)

### Token and Basic Auth Services
- **[JWT Token Service](jwt_credential_example.py)** - JWT token generation and validation
- **[HTTP Basic Auth](http_basic_auth_example.py)** - Username/password authentication

## Prerequisites

Before running these examples, ensure you have:

1. **Google ADK installed**: `pip install google-adk`
2. **This package installed**: `pip install google-adk-extras`
3. **Required dependencies**: `pip install PyJWT` (for JWT examples)

## OAuth2 Setup Requirements

For OAuth2 examples, you'll need to set up applications with the respective providers:

### Google OAuth2
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select existing one
3. Enable the APIs you want to use (Calendar API, Gmail API, etc.)
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Configure OAuth consent screen
6. Add authorized redirect URIs (e.g., `http://localhost:8000/callback`)

### GitHub OAuth2
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Set Authorization callback URL (e.g., `http://localhost:8000/callback`)
4. Note the Client ID and Client Secret

### Microsoft OAuth2
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to Azure Active Directory → App registrations
3. Click "New registration"
4. Configure redirect URI (e.g., `http://localhost:8000/callback`)
5. Add required API permissions (Microsoft Graph)

### X (Twitter) OAuth2
1. Go to [X Developer Portal](https://developer.twitter.com/)
2. Create a new app
3. Configure OAuth 2.0 settings
4. Add callback URL (e.g., `http://localhost:8000/callback`)

## Running Examples

Most examples require environment variables for security:

```bash
# Google OAuth2
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"

# GitHub OAuth2
export GITHUB_CLIENT_ID="your-github-client-id"
export GITHUB_CLIENT_SECRET="your-github-client-secret"

# Microsoft OAuth2
export MICROSOFT_TENANT_ID="common"  # or your specific tenant ID
export MICROSOFT_CLIENT_ID="your-azure-client-id"
export MICROSOFT_CLIENT_SECRET="your-azure-client-secret"

# X OAuth2
export X_CLIENT_ID="your-x-client-id"
export X_CLIENT_SECRET="your-x-client-secret"

# JWT
export JWT_SECRET="your-jwt-signing-secret"

# Basic Auth
export BASIC_AUTH_USERNAME="your-username"
export BASIC_AUTH_PASSWORD="your-password"
```

Then run any example:
```bash
python examples/credentials/google_oauth2_example.py
```

## Integration with Agents

All credential services can be used with Google ADK agents and runners:

```python
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google_adk_extras.credentials import GoogleOAuth2CredentialService

# Setup credential service
credential_service = GoogleOAuth2CredentialService(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scopes=["openid", "calendar"]
)
await credential_service.initialize()

# Setup session service
session_service = InMemorySessionService()

# Create agent and runner
agent = Agent(name="my_agent", model="gemini-2.0-flash")
runner = Runner(
    agent=agent,
    session_service=session_service,
    credential_service=credential_service,
    app_name="my_app"
)
```

## Security Notes

- **Never commit credentials**: Use environment variables or secure secret management
- **Use HTTPS**: Always use secure connections for OAuth2 flows
- **Token Storage**: Be careful with token storage - consider encryption for production
- **Scope Minimization**: Only request the minimum scopes needed
- **Token Rotation**: Implement proper token refresh and rotation strategies