#!/usr/bin/env python3
"""Example of using Microsoft OAuth2 credential service."""

import os
import asyncio
from google_adk_extras.credentials import MicrosoftOAuth2CredentialService


async def main():
    """Demonstrate Microsoft OAuth2 credential service usage."""
    print("Microsoft OAuth2 Credential Service Example")
    print("=" * 50)
    
    # Get credentials from environment variables
    client_id = os.environ.get("MICROSOFT_CLIENT_ID")
    client_secret = os.environ.get("MICROSOFT_CLIENT_SECRET")
    tenant_id = os.environ.get("MICROSOFT_TENANT_ID", "common")
    
    if not client_id or not client_secret:
        print("Error: Please set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET environment variables")
        print("Optionally set MICROSOFT_TENANT_ID (defaults to 'common' for multi-tenant)")
        print("\nTo get these credentials:")
        print("1. Go to https://portal.azure.com/")
        print("2. Navigate to Azure Active Directory")
        print("3. Go to App registrations → New registration")
        print("4. Fill in the application details")
        print("5. Set Redirect URI")
        print("6. Get Application (client) ID and create a Client secret")
        return
    
    # Initialize Microsoft OAuth2 credential service
    credential_service = MicrosoftOAuth2CredentialService(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "User.Read",         # Read user profile
            "Mail.Read",         # Read user email
            "Files.Read",        # Read OneDrive files
            "Calendars.Read",    # Read calendar events
            "offline_access"     # Maintain access when offline
        ],
        use_session_state=False  # Use in-memory storage for demo
    )
    
    try:
        # Initialize the service
        print("Initializing Microsoft OAuth2 credential service...")
        await credential_service.initialize()
        print("✓ Service initialized successfully")
        
        # Display supported scopes
        print("\nSupported Microsoft OAuth2 scopes:")
        scopes = credential_service.get_supported_scopes()
        for scope_name, description in scopes.items():
            print(f"  {scope_name:<20} - {description}")
        
        # Create auth configuration
        print("\nCreating OAuth2 authentication configuration...")
        auth_config = credential_service.create_auth_config()
        print("✓ Auth config created")
        
        # Display OAuth2 flow information
        oauth_flows = auth_config.auth_scheme.flows
        auth_code_flow = oauth_flows.authorizationCode
        
        print(f"\nOAuth2 Flow Configuration:")
        print(f"  Authorization URL: {auth_code_flow.authorizationUrl}")
        print(f"  Token URL: {auth_code_flow.tokenUrl}")
        print(f"  Tenant ID: {tenant_id}")
        print(f"  Requested Scopes:")
        for scope, desc in auth_code_flow.scopes.items():
            print(f"    - {scope}: {desc}")
        
        # Display credential information
        raw_credential = auth_config.raw_auth_credential
        print(f"\nCredential Configuration:")
        print(f"  Auth Type: {raw_credential.auth_type}")
        print(f"  Client ID: {raw_credential.oauth2.client_id}")
        print(f"  Client Secret: {'*' * len(raw_credential.oauth2.client_secret)}")
        
        print("\nTo complete the OAuth2 flow:")
        print("1. User would be redirected to Microsoft authorization URL")
        print("2. After consent, they'd be redirected back with an authorization code")
        print("3. The service would exchange the code for access/refresh tokens")
        print("4. Tokens would be stored securely using the credential service")
        
        print("\n📝 Note: This example demonstrates service setup and configuration.")
        print("   In a real application, you would integrate this with Google ADK's")
        print("   Runner and Agent to handle the complete OAuth2 flow automatically.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await credential_service.cleanup()
        print("\n✓ Service cleaned up")


async def demonstrate_tenant_configurations():
    """Show different tenant configuration examples."""
    print("\n" + "=" * 60)
    print("Microsoft Tenant Configuration Examples")
    print("=" * 60)
    
    examples = [
        {
            "name": "Multi-tenant (common)",
            "tenant_id": "common",
            "description": "Allows users from any Azure AD tenant to sign in"
        },
        {
            "name": "Organizations only",
            "tenant_id": "organizations", 
            "description": "Allows users from any organizational tenant to sign in"
        },
        {
            "name": "Specific tenant",
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "description": "Allows users from specific tenant only"
        }
    ]
    
    for example in examples:
        print(f"\n{example['name']}:")
        print(f"  tenant_id: '{example['tenant_id']}'")
        print(f"  Description: {example['description']}")


async def demonstrate_integration_pattern():
    """Show how to integrate with Google ADK Runner."""
    print("\n" + "=" * 60)
    print("Google ADK Integration Pattern")
    print("=" * 60)
    
    integration_code = '''
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService  
from google_adk_extras.credentials import MicrosoftOAuth2CredentialService

async def setup_microsoft_integration():
    """Setup Microsoft OAuth2 with ADK Runner."""
    
    # Initialize credential service
    credential_service = MicrosoftOAuth2CredentialService(
        tenant_id=os.environ.get("MICROSOFT_TENANT_ID", "common"),
        client_id=os.environ["MICROSOFT_CLIENT_ID"],
        client_secret=os.environ["MICROSOFT_CLIENT_SECRET"],
        scopes=["User.Read", "Mail.Read", "Calendars.Read"]
    )
    await credential_service.initialize()
    
    # Setup other services
    session_service = InMemorySessionService()
    
    # Create agent with tools that require Microsoft Graph API
    agent = Agent(
        name="microsoft_assistant",
        model="gemini-2.0-flash",
        instruction="You can access Microsoft 365 services on behalf of users.",
        tools=[]  # Add Microsoft Graph API tools here
    )
    
    # Create runner with credential service
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,  # This enables OAuth2 auth
        app_name="microsoft_integration_app"
    )
    
    return runner

# Usage
runner = await setup_microsoft_integration()
'''
    print(integration_code)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_tenant_configurations())
    asyncio.run(demonstrate_integration_pattern())