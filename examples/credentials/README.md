# Credential Services Examples

This directory contains comprehensive examples for all credential service implementations, demonstrating production-ready authentication and authorization with popular OAuth2 providers and token systems.

## Available Credential Services

### 🔐 OAuth2 Providers
- **[Google OAuth2](google_oauth2_example.py)** - Google APIs authentication
  - Google Calendar, Gmail, Drive, Sheets, Photos, YouTube
  - Google Cloud Platform APIs
  - Firebase and Google Analytics
  - Automatic token refresh and error handling

- **[GitHub OAuth2](github_oauth2_example.py)** - GitHub API authentication  
  - Repository access and management
  - User profile and organization data
  - GitHub Actions and CI/CD integration
  - Enterprise GitHub support

- **[Microsoft OAuth2](microsoft_oauth2_example.py)** - Microsoft Graph API authentication
  - Outlook email and calendar integration
  - Teams and SharePoint collaboration
  - OneDrive file storage and sharing
  - Azure Active Directory integration

- **[X (Twitter) OAuth2](x_oauth2_example.py)** - X API v2 authentication
  - Tweet posting and timeline access
  - User profile and follower management
  - Spaces and direct message integration
  - Advanced search and analytics

### 🎫 Token and Authentication Services  
- **[JWT Token Service](jwt_credential_example.py)** - JWT token management
  - Token generation with custom claims
  - Token validation and verification
  - Refresh token handling
  - Role-based access control (RBAC)

- **[HTTP Basic Auth](http_basic_auth_example.py)** - Username/password authentication
  - Secure credential storage
  - Password hashing and validation
  - Session management integration
  - Multi-factor authentication support

## Features Demonstrated

Each example showcases:

### Core Authentication Features
- **OAuth2 Flows**: Authorization code flow with PKCE
- **Token Management**: Automatic refresh and secure storage
- **Scope Management**: Granular permission handling
- **Error Handling**: Graceful handling of authentication failures
- **Security**: Best practices for credential handling

### Integration Patterns
- **Agent Integration**: Using credentials with Google ADK agents
- **Session Persistence**: Storing credentials across sessions
- **Multi-user Support**: Managing credentials for multiple users
- **Configuration**: Environment-based credential configuration

### Production Features
- **Token Refresh**: Automatic token renewal
- **Rate Limiting**: Handling API rate limits
- **Error Recovery**: Retry logic and fallback strategies
- **Monitoring**: Authentication event logging and metrics

## Prerequisites

- **Python 3.10+**
- **Google ADK**: `pip install google-adk`
- **This Package**: `pip install google-adk-extras`
- **JWT Support**: `pip install PyJWT cryptography` (for JWT examples)

## OAuth2 Provider Setup

### 🟦 Google OAuth2 Setup
1. **Google Cloud Console**: Visit [console.cloud.google.com](https://console.cloud.google.com/)
2. **Create Project**: Create or select a Google Cloud project
3. **Enable APIs**: Enable required APIs (Calendar, Gmail, Drive, etc.)
4. **Create Credentials**:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Web application"
   - Add authorized redirect URIs: `http://localhost:8000/callback`
5. **OAuth Consent Screen**: Configure consent screen with required information
6. **Scopes**: Add necessary scopes for your application

### 🐙 GitHub OAuth2 Setup
1. **GitHub Settings**: Go to Settings → Developer settings → OAuth Apps
2. **New OAuth App**: Click "New OAuth App"
3. **Application Details**:
   - Application name: Your app name
   - Homepage URL: Your application URL
   - Authorization callback URL: `http://localhost:8000/callback`
4. **Permissions**: Configure repository and user permissions
5. **Client Credentials**: Note Client ID and generate Client Secret

### 🔷 Microsoft OAuth2 Setup  
1. **Azure Portal**: Visit [portal.azure.com](https://portal.azure.com/)
2. **App Registration**: Azure Active Directory → App registrations → New registration
3. **Application Configuration**:
   - Name: Your application name
   - Supported account types: Choose appropriate option
   - Redirect URI: `http://localhost:8000/callback`
4. **API Permissions**: Add Microsoft Graph permissions
5. **Certificates & Secrets**: Create client secret

### ❌ X (Twitter) OAuth2 Setup
1. **Developer Portal**: Visit [developer.twitter.com](https://developer.twitter.com/)
2. **Create App**: Apply for developer account and create new app
3. **OAuth 2.0 Settings**:
   - Type of App: Web App
   - Callback URI: `http://localhost:8000/callback`
   - Website URL: Your application URL
4. **Permissions**: Configure required permissions (read, write, etc.)
5. **Keys and Tokens**: Generate API keys and bearer token

## Running Examples

### Environment Configuration

Set up environment variables for secure credential management:

```bash
# Google OAuth2
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:8000/callback"

# GitHub OAuth2  
export GITHUB_CLIENT_ID="your-github-client-id"
export GITHUB_CLIENT_SECRET="your-github-client-secret"
export GITHUB_REDIRECT_URI="http://localhost:8000/callback"

# Microsoft OAuth2
export MICROSOFT_TENANT_ID="common"  # or your specific tenant ID
export MICROSOFT_CLIENT_ID="your-azure-client-id"
export MICROSOFT_CLIENT_SECRET="your-azure-client-secret"
export MICROSOFT_REDIRECT_URI="http://localhost:8000/callback"

# X (Twitter) OAuth2
export X_CLIENT_ID="your-x-client-id"
export X_CLIENT_SECRET="your-x-client-secret"
export X_REDIRECT_URI="http://localhost:8000/callback"

# JWT Token Service
export JWT_SECRET="your-jwt-signing-secret-key"
export JWT_ALGORITHM="HS256"  # or RS256 for RSA keys

# HTTP Basic Auth
export BASIC_AUTH_USERNAME="your-username"
export BASIC_AUTH_PASSWORD="your-password"
```

### Quick Start

```bash
cd /path/to/google-adk-extras

# OAuth2 Examples (require provider setup)
uv run python examples/credentials/google_oauth2_example.py
uv run python examples/credentials/github_oauth2_example.py
uv run python examples/credentials/microsoft_oauth2_example.py
uv run python examples/credentials/x_oauth2_example.py

# Token Examples (work without external setup)
uv run python examples/credentials/jwt_credential_example.py
uv run python examples/credentials/http_basic_auth_example.py
```

### Development Mode

For testing OAuth2 flows locally:

```bash
# Install additional development dependencies
pip install uvicorn fastapi

# Run OAuth2 example with local callback server
DEVELOPMENT_MODE=true uv run python examples/credentials/google_oauth2_example.py
```

## Integration Examples

### With Google ADK Agents and Runners

```python
import os
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google_adk_extras.credentials import GoogleOAuth2CredentialService

# Setup Google OAuth2 credential service
credential_service = GoogleOAuth2CredentialService(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scopes=["openid", "email", "https://www.googleapis.com/auth/calendar.readonly"]
)
await credential_service.initialize()

# Setup session service
session_service = InMemorySessionService()

# Create agent with calendar access
agent = Agent(
    name="calendar-assistant",
    model="gemini-2.0-flash",
    instructions="You can help users manage their Google Calendar"
)

# Create runner with credentials
runner = Runner(
    agent=agent,
    session_service=session_service,
    credential_service=credential_service,
    app_name="calendar-assistant"
)

# Use in conversation
result = await runner.run(
    "What meetings do I have today?",
    user_id="user_123"
)
```

### Multi-Provider Credential Management

```python
from google_adk_extras.credentials import (
    GoogleOAuth2CredentialService,
    GitHubOAuth2CredentialService,
    MicrosoftOAuth2CredentialService
)

class MultiProviderCredentialManager:
    """Manage credentials across multiple OAuth2 providers"""
    
    def __init__(self):
        self.providers = {}
    
    async def add_provider(self, name: str, service):
        """Add a credential provider"""
        await service.initialize()
        self.providers[name] = service
    
    async def get_user_credentials(self, provider_name: str, user_id: str):
        """Get credentials for a specific provider and user"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not configured")
        
        provider = self.providers[provider_name]
        return await provider.get_credentials(user_id)
    
    async def refresh_all_tokens(self, user_id: str):
        """Refresh tokens across all providers for a user"""
        refreshed = {}
        
        for name, provider in self.providers.items():
            try:
                credentials = await provider.get_credentials(user_id)
                if credentials and hasattr(provider, 'refresh_token'):
                    new_credentials = await provider.refresh_token(credentials)
                    refreshed[name] = new_credentials
            except Exception as e:
                print(f"Failed to refresh {name} tokens for {user_id}: {e}")
        
        return refreshed

# Usage
manager = MultiProviderCredentialManager()

# Add providers
await manager.add_provider("google", google_oauth2_service)
await manager.add_provider("github", github_oauth2_service) 
await manager.add_provider("microsoft", microsoft_oauth2_service)

# Get credentials
google_creds = await manager.get_user_credentials("google", "user_123")
github_creds = await manager.get_user_credentials("github", "user_123")
```

### JWT-based Authentication System

```python
from google_adk_extras.credentials import JWTCredentialService
import datetime

# Create JWT service
jwt_service = JWTCredentialService(
    secret=os.environ["JWT_SECRET"],
    algorithm="HS256"
)

# User authentication example
async def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user and return JWT tokens"""
    
    # Verify credentials (implement your own logic)
    if verify_user_credentials(username, password):
        # Create JWT with user claims
        user_claims = {
            "user_id": username,
            "roles": ["user"],
            "permissions": ["read", "write"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        
        # Generate tokens
        access_token = await jwt_service.generate_token(user_claims)
        refresh_token = await jwt_service.generate_refresh_token({"user_id": username})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600
        }
    else:
        raise ValueError("Invalid credentials")

# Token validation middleware
async def validate_jwt_token(token: str) -> dict:
    """Validate JWT token and return user claims"""
    
    try:
        claims = await jwt_service.validate_token(token)
        return claims
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")

# Usage with agents
async def create_authenticated_runner(token: str):
    """Create runner with JWT authentication"""
    
    # Validate token
    user_claims = await validate_jwt_token(token)
    user_id = user_claims["user_id"]
    
    # Create session service with user context
    session_service = SQLSessionService("sqlite:///sessions.db")
    await session_service.initialize()
    
    # Create agent
    agent = Agent(
        name="authenticated-assistant",
        model="gemini-2.0-flash"
    )
    
    # Create runner with user context
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="secure-app"
    )
    
    return runner, user_id
```

### OAuth2 Token Refresh and Management

```python
import asyncio
from datetime import datetime, timedelta

class TokenManager:
    """Automatic token refresh and management"""
    
    def __init__(self, credential_service):
        self.credential_service = credential_service
        self.refresh_tasks = {}
    
    async def start_auto_refresh(self, user_id: str):
        """Start automatic token refresh for a user"""
        
        if user_id in self.refresh_tasks:
            return  # Already running
        
        task = asyncio.create_task(self._refresh_loop(user_id))
        self.refresh_tasks[user_id] = task
    
    async def stop_auto_refresh(self, user_id: str):
        """Stop automatic token refresh for a user"""
        
        if user_id in self.refresh_tasks:
            task = self.refresh_tasks.pop(user_id)
            task.cancel()
    
    async def _refresh_loop(self, user_id: str):
        """Background loop to refresh tokens"""
        
        while True:
            try:
                credentials = await self.credential_service.get_credentials(user_id)
                
                if credentials and 'expires_at' in credentials:
                    expires_at = datetime.fromisoformat(credentials['expires_at'])
                    now = datetime.utcnow()
                    
                    # Refresh if expires within 5 minutes
                    if expires_at - now < timedelta(minutes=5):
                        print(f"Refreshing tokens for user {user_id}")
                        await self.credential_service.refresh_token(credentials)
                
                # Check every minute
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Token refresh error for {user_id}: {e}")
                await asyncio.sleep(60)  # Continue despite errors

# Usage
google_service = GoogleOAuth2CredentialService(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    scopes=["openid", "email"]
)

token_manager = TokenManager(google_service)

# Start automatic refresh for a user
await token_manager.start_auto_refresh("user_123")

# Stop when done
await token_manager.stop_auto_refresh("user_123")
```

## Advanced Usage Patterns

### Secure Token Storage

```python
from cryptography.fernet import Fernet
import json
import os

class SecureTokenStorage:
    """Encrypted token storage for production use"""
    
    def __init__(self, encryption_key: bytes = None):
        if encryption_key is None:
            encryption_key = os.environ.get("TOKEN_ENCRYPTION_KEY", "").encode()
        
        if not encryption_key:
            # Generate new key (store this securely!)
            encryption_key = Fernet.generate_key()
            print(f"Generated encryption key: {encryption_key.decode()}")
        
        self.cipher = Fernet(encryption_key)
    
    def encrypt_token(self, token_data: dict) -> str:
        """Encrypt token data"""
        json_data = json.dumps(token_data)
        encrypted_data = self.cipher.encrypt(json_data.encode())
        return encrypted_data.decode()
    
    def decrypt_token(self, encrypted_token: str) -> dict:
        """Decrypt token data"""
        decrypted_data = self.cipher.decrypt(encrypted_token.encode())
        return json.loads(decrypted_data.decode())

# Usage with credential service
storage = SecureTokenStorage()

# Store credentials securely
credentials = await google_service.get_credentials("user_123")
encrypted_creds = storage.encrypt_token(credentials)

# Store encrypted_creds in database or file
# Later, retrieve and decrypt
decrypted_creds = storage.decrypt_token(encrypted_creds)
```

### Role-Based Access Control

```python
from enum import Enum

class Permission(Enum):
    READ_CALENDAR = "calendar:read"
    WRITE_CALENDAR = "calendar:write"
    READ_EMAIL = "email:read"
    SEND_EMAIL = "email:send"

class Role(Enum):
    USER = "user"
    ADMIN = "admin"
    SERVICE = "service"

# Role permission mapping
ROLE_PERMISSIONS = {
    Role.USER: [Permission.READ_CALENDAR, Permission.READ_EMAIL],
    Role.ADMIN: [Permission.READ_CALENDAR, Permission.WRITE_CALENDAR, 
                 Permission.READ_EMAIL, Permission.SEND_EMAIL],
    Role.SERVICE: [Permission.READ_CALENDAR, Permission.WRITE_CALENDAR]
}

async def create_user_jwt(user_id: str, role: Role) -> str:
    """Create JWT with role-based permissions"""
    
    permissions = [p.value for p in ROLE_PERMISSIONS.get(role, [])]
    
    claims = {
        "user_id": user_id,
        "role": role.value,
        "permissions": permissions,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    
    return await jwt_service.generate_token(claims)

async def check_permission(token: str, required_permission: Permission) -> bool:
    """Check if token has required permission"""
    
    try:
        claims = await jwt_service.validate_token(token)
        user_permissions = claims.get("permissions", [])
        return required_permission.value in user_permissions
    except:
        return False

# Usage in agent tools
async def calendar_tool_with_auth(token: str, action: str, **kwargs):
    """Calendar tool with permission checking"""
    
    if action == "read" and not await check_permission(token, Permission.READ_CALENDAR):
        raise PermissionError("Calendar read permission required")
    
    if action == "write" and not await check_permission(token, Permission.WRITE_CALENDAR):
        raise PermissionError("Calendar write permission required")
    
    # Proceed with calendar operation
    credentials = await google_service.get_credentials_from_token(token)
    # ... perform calendar operation
```

## Security Best Practices

### Production Security Checklist

```python
# ✅ Use environment variables for secrets
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
if not client_secret:
    raise ValueError("GOOGLE_CLIENT_SECRET environment variable required")

# ✅ Use HTTPS redirect URIs in production
redirect_uri = "https://yourdomain.com/oauth/callback"  # Not http://

# ✅ Implement token encryption
encrypted_tokens = encrypt_sensitive_data(tokens)

# ✅ Set appropriate token expiration
jwt_claims = {
    "exp": datetime.utcnow() + timedelta(hours=1),  # Short-lived tokens
    "iat": datetime.utcnow(),
    "nbf": datetime.utcnow()
}

# ✅ Validate all inputs
def validate_user_input(user_input: str) -> str:
    # Sanitize and validate input
    if not user_input or len(user_input) > 1000:
        raise ValueError("Invalid input")
    return user_input.strip()

# ✅ Log security events
import logging
security_logger = logging.getLogger("security")

async def log_authentication_event(user_id: str, provider: str, success: bool):
    """Log authentication events for monitoring"""
    
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "provider": provider,
        "success": success,
        "ip_address": "...",  # Get from request
        "user_agent": "..."   # Get from request
    }
    
    security_logger.info(f"Auth event: {event}")
```

## Troubleshooting

### Common OAuth2 Issues

1. **Invalid Redirect URI**
   ```bash
   # Ensure redirect URI matches exactly in provider settings
   export GOOGLE_REDIRECT_URI="http://localhost:8000/callback"
   ```

2. **Scope Permission Errors**
   ```python
   # Check if required scopes are properly configured
   scopes = ["openid", "email", "https://www.googleapis.com/auth/calendar.readonly"]
   ```

3. **Token Refresh Failures**
   ```python
   # Implement proper error handling for token refresh
   try:
       new_token = await service.refresh_token(old_token)
   except Exception as e:
       # Handle refresh failure - may need re-authentication
       print(f"Token refresh failed: {e}")
   ```

### Debug Mode

Enable detailed logging for credential services:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable credential service debugging
logging.getLogger('google_adk_extras.credentials').setLevel(logging.DEBUG)
```

## Production Deployment Notes

- **Environment Variables**: Use secure secret management systems
- **HTTPS Only**: Always use HTTPS for OAuth2 redirects in production
- **Token Storage**: Implement encrypted storage for sensitive tokens
- **Rate Limiting**: Implement proper rate limiting for auth endpoints
- **Monitoring**: Set up monitoring for authentication events and failures
- **Backup**: Have backup authentication methods for critical systems