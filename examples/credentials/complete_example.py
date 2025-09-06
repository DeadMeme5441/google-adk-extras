#!/usr/bin/env python3
"""
Complete Credential Services Example

This example demonstrates how to use all available credential services
and shows patterns for choosing the right service for different scenarios.
"""

import os
import asyncio
from google_adk_extras.credentials import (
    GoogleOAuth2CredentialService,
    GitHubOAuth2CredentialService, 
    MicrosoftOAuth2CredentialService,
    XOAuth2CredentialService,
    JWTCredentialService,
    HTTPBasicAuthCredentialService
)


async def demonstrate_oauth2_services():
    """Show all OAuth2 credential services."""
    print("OAuth2 Credential Services")
    print("=" * 50)
    
    oauth2_services = [
        {
            "name": "Google OAuth2",
            "service": GoogleOAuth2CredentialService(
                client_id="demo-google-client-id",
                client_secret="demo-secret",
                scopes=["openid", "calendar", "gmail.readonly"],
                use_session_state=False
            ),
            "use_cases": [
                "Google Calendar integration",
                "Gmail API access", 
                "Google Drive file management",
                "Google Workspace automation"
            ]
        },
        {
            "name": "GitHub OAuth2", 
            "service": GitHubOAuth2CredentialService(
                client_id="demo-github-client-id",
                client_secret="demo-secret",
                scopes=["user", "repo", "gist"],
                use_session_state=False
            ),
            "use_cases": [
                "Repository management",
                "Issue and PR automation",
                "Gist creation and management",
                "Organization access"
            ]
        },
        {
            "name": "Microsoft OAuth2",
            "service": MicrosoftOAuth2CredentialService(
                tenant_id="common",
                client_id="demo-ms-client-id", 
                client_secret="demo-secret",
                scopes=["User.Read", "Mail.Read", "Files.Read"],
                use_session_state=False
            ),
            "use_cases": [
                "Microsoft 365 integration",
                "Outlook email access",
                "OneDrive file management", 
                "Azure AD user management"
            ]
        },
        {
            "name": "X (Twitter) OAuth2",
            "service": XOAuth2CredentialService(
                client_id="demo-x-client-id",
                client_secret="demo-secret", 
                scopes=["tweet.read", "tweet.write", "users.read"],
                use_session_state=False
            ),
            "use_cases": [
                "Tweet automation",
                "Social media monitoring",
                "User engagement tracking",
                "Content scheduling"
            ]
        }
    ]
    
    for oauth_config in oauth2_services:
        print(f"\n{oauth_config['name']}:")
        print(f"  Use Cases:")
        for use_case in oauth_config['use_cases']:
            print(f"    - {use_case}")
        
        try:
            service = oauth_config['service']
            await service.initialize()
            auth_config = service.create_auth_config()
            
            # Get OAuth flow info
            oauth_flow = auth_config.auth_scheme.flows.authorizationCode
            print(f"  Authorization URL: {oauth_flow.authorizationUrl}")
            print(f"  Scopes: {list(oauth_flow.scopes.keys())}")
            
            await service.cleanup()
            print(f"  ✓ {oauth_config['name']} service validated")
        except Exception as e:
            print(f"  ✗ {oauth_config['name']} error: {e}")


async def demonstrate_token_based_services():
    """Show JWT and HTTP Basic Auth services."""
    print("\n" + "=" * 60)
    print("Token-Based and Basic Auth Services")
    print("=" * 60)
    
    # JWT Service
    print("\nJWT Credential Service:")
    print("  Use Cases:")
    print("    - API-to-API authentication")
    print("    - Stateless session management")
    print("    - Microservices authentication")
    print("    - Custom token-based APIs")
    
    jwt_service = JWTCredentialService(
        secret="demo-jwt-secret",
        algorithm="HS256",
        issuer="demo-app",
        audience="api.example.com",
        custom_claims={"role": "admin"},
        use_session_state=False
    )
    
    try:
        await jwt_service.initialize()
        
        # Generate a token
        token = jwt_service.generate_jwt_token("demo_user")
        print(f"  Sample JWT: {token[:50]}...")
        
        # Verify token
        payload = jwt_service.verify_jwt_token(token)
        print(f"  Token payload: {payload}")
        
        await jwt_service.cleanup()
        print("  ✓ JWT service validated")
    except Exception as e:
        print(f"  ✗ JWT service error: {e}")
    
    # HTTP Basic Auth Service
    print("\nHTTP Basic Auth Service:")
    print("  Use Cases:")
    print("    - Legacy API authentication")
    print("    - Simple username/password APIs")
    print("    - Internal service authentication")
    print("    - Development and testing")
    
    basic_auth_service = HTTPBasicAuthCredentialService(
        username="demo_user",
        password="demo_password",
        realm="Demo API",
        use_session_state=False
    )
    
    try:
        await basic_auth_service.initialize()
        
        # Generate auth header
        auth_header = basic_auth_service.get_auth_header()
        print(f"  Authorization header: {auth_header}")
        
        # Validate credentials
        is_valid = basic_auth_service.validate_credentials("demo_user", "demo_password")
        print(f"  Credential validation: {is_valid}")
        
        await basic_auth_service.cleanup()
        print("  ✓ Basic Auth service validated")
    except Exception as e:
        print(f"  ✗ Basic Auth service error: {e}")


async def demonstrate_service_selection_guide():
    """Provide guidance on selecting the right credential service."""
    print("\n" + "=" * 60)
    print("Credential Service Selection Guide")
    print("=" * 60)
    
    selection_guide = {
        "Google OAuth2": {
            "when_to_use": [
                "Integrating with Google services (Calendar, Gmail, Drive, etc.)",
                "Need user consent for Google data access",
                "Building Google Workspace extensions",
                "Implementing Google Sign-In"
            ],
            "setup_requirements": [
                "Google Cloud Console project",
                "OAuth2 client credentials",
                "Configured OAuth consent screen",
                "Redirect URI configuration"
            ]
        },
        "GitHub OAuth2": {
            "when_to_use": [
                "GitHub repository automation",
                "Code analysis and management tools",
                "Developer productivity tools",
                "GitHub data analysis"
            ],
            "setup_requirements": [
                "GitHub Developer account",
                "OAuth App registration",
                "GitHub API permissions",
                "Webhook configuration (optional)"
            ]
        },
        "Microsoft OAuth2": {
            "when_to_use": [
                "Microsoft 365 integration",
                "Azure AD authentication",
                "Outlook/Exchange integration",
                "OneDrive/SharePoint access"
            ],
            "setup_requirements": [
                "Azure AD tenant",
                "App registration in Azure portal",
                "API permissions configuration",
                "Multi-tenant considerations"
            ]
        },
        "X (Twitter) OAuth2": {
            "when_to_use": [
                "Social media automation",
                "Tweet scheduling and management",
                "Social listening applications",
                "Content engagement tracking"
            ],
            "setup_requirements": [
                "Twitter Developer account",
                "X API application",
                "OAuth2 configuration",
                "Rate limiting considerations"
            ]
        },
        "JWT": {
            "when_to_use": [
                "API-to-API authentication",
                "Stateless authentication",
                "Microservices architecture",
                "Custom authentication systems"
            ],
            "setup_requirements": [
                "Secure secret management",
                "Token expiration strategy",
                "Refresh mechanism",
                "Signature verification"
            ]
        },
        "HTTP Basic Auth": {
            "when_to_use": [
                "Simple API authentication",
                "Legacy system integration",
                "Development and testing",
                "Internal service communication"
            ],
            "setup_requirements": [
                "HTTPS enforcement",
                "Credential management",
                "Basic security considerations",
                "Rate limiting"
            ]
        }
    }
    
    for service_name, guide in selection_guide.items():
        print(f"\n{service_name}:")
        print("  When to use:")
        for use_case in guide['when_to_use']:
            print(f"    ✓ {use_case}")
        print("  Setup requirements:")
        for requirement in guide['setup_requirements']:
            print(f"    • {requirement}")


async def demonstrate_integration_patterns():
    """Show common integration patterns with Google ADK."""
    print("\n" + "=" * 60)
    print("Google ADK Integration Patterns")
    print("=" * 60)
    
    integration_code = '''
# Pattern 1: Single OAuth2 Service Integration
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google_adk_extras.credentials import GoogleOAuth2CredentialService

async def setup_single_oauth_integration():
    """Setup with single OAuth2 provider."""
    credential_service = GoogleOAuth2CredentialService(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=["calendar", "gmail.readonly"]
    )
    await credential_service.initialize()
    
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,
        app_name="single_oauth_app"
    )
    return runner

# Pattern 2: JWT-based API Authentication  
from google_adk_extras.credentials import JWTCredentialService

async def setup_jwt_api_integration():
    """Setup with JWT for API access."""
    credential_service = JWTCredentialService(
        secret=os.environ["JWT_SECRET"],
        issuer="my-app",
        audience="api.example.com",
        expiration_minutes=120
    )
    await credential_service.initialize()
    
    runner = Runner(
        agent=agent,
        session_service=session_service, 
        credential_service=credential_service,
        app_name="jwt_api_app"
    )
    return runner

# Pattern 3: Multi-Provider Support (Advanced)
async def setup_multi_provider_app():
    """Setup app that can switch between credential providers."""
    
    # Initialize multiple credential services
    google_creds = GoogleOAuth2CredentialService(...)
    github_creds = GitHubOAuth2CredentialService(...)
    jwt_creds = JWTCredentialService(...)
    
    # Store in a credential manager/factory
    credential_manager = {
        "google": google_creds,
        "github": github_creds, 
        "jwt": jwt_creds
    }
    
    # Initialize all services
    for service in credential_manager.values():
        await service.initialize()
    
    # Use different credentials based on user preference or context
    def get_credential_service(provider: str):
        return credential_manager.get(provider)
    
    # Create runner with appropriate credential service
    active_provider = "google"  # or from user/context
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=get_credential_service(active_provider),
        app_name="multi_provider_app"
    )
    
    return runner, credential_manager
'''
    print(integration_code)


async def main():
    """Main demonstration function."""
    print("Google ADK Extras - Complete Credential Services Example")
    print("=" * 60)
    print("This example demonstrates all available credential services")
    print("and provides guidance on when and how to use each one.")
    print()
    
    try:
        await demonstrate_oauth2_services()
        await demonstrate_token_based_services()
        await demonstrate_service_selection_guide()
        await demonstrate_integration_patterns()
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print("✓ All credential services validated")
        print("✓ OAuth2 services: Google, GitHub, Microsoft, X")
        print("✓ Token-based services: JWT") 
        print("✓ Basic authentication: HTTP Basic Auth")
        print("✓ Integration patterns demonstrated")
        print()
        print("Next Steps:")
        print("1. Choose appropriate credential service for your use case")
        print("2. Set up credentials with the respective provider")
        print("3. Configure environment variables")
        print("4. Integrate with Google ADK Runner and Agent")
        print("5. Test authentication flow end-to-end")
        
    except Exception as e:
        print(f"Error in demonstration: {e}")


if __name__ == "__main__":
    asyncio.run(main())