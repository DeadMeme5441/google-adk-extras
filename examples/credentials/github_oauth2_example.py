#!/usr/bin/env python3
"""Example of using GitHub OAuth2 credential service."""

import os
import asyncio
from google_adk_extras.credentials import GitHubOAuth2CredentialService


async def main():
    """Demonstrate GitHub OAuth2 credential service usage."""
    print("GitHub OAuth2 Credential Service Example")
    print("=" * 50)
    
    # Get credentials from environment variables
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables")
        print("\nTo get these credentials:")
        print("1. Go to https://github.com/settings/developers")
        print("2. Click 'New OAuth App'")
        print("3. Fill in the application details")
        print("4. Set Authorization callback URL")
        print("5. Get Client ID and Client Secret")
        return
    
    # Initialize GitHub OAuth2 credential service
    credential_service = GitHubOAuth2CredentialService(
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "user",              # Access user profile
            "user:email",        # Access user email
            "repo",              # Access repositories
            "read:org",          # Read organization membership
            "gist"               # Access gists
        ],
        use_session_state=False  # Use in-memory storage for demo
    )
    
    try:
        # Initialize the service
        print("Initializing GitHub OAuth2 credential service...")
        await credential_service.initialize()
        print("✓ Service initialized successfully")
        
        # Display supported scopes
        print("\nSupported GitHub OAuth2 scopes:")
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
        print("1. User would be redirected to GitHub authorization URL")
        print("2. After consent, they'd be redirected back with an authorization code")
        print("3. The service would exchange the code for access tokens")
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


async def demonstrate_integration_pattern():
    """Show how to integrate with Google ADK Runner."""
    print("\n" + "=" * 60)
    print("Google ADK Integration Pattern")
    print("=" * 60)
    
    integration_code = '''
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService  
from google_adk_extras.credentials import GitHubOAuth2CredentialService

async def setup_github_integration():
    """Setup GitHub OAuth2 with ADK Runner."""
    
    # Initialize credential service
    credential_service = GitHubOAuth2CredentialService(
        client_id=os.environ["GITHUB_CLIENT_ID"],
        client_secret=os.environ["GITHUB_CLIENT_SECRET"],
        scopes=["user", "repo", "gist"]
    )
    await credential_service.initialize()
    
    # Setup other services
    session_service = InMemorySessionService()
    
    # Create agent with tools that require GitHub OAuth2
    agent = Agent(
        name="github_assistant",
        model="gemini-2.0-flash",
        instruction="You can access GitHub repositories and user data on behalf of users.",
        tools=[]  # Add GitHub API tools here
    )
    
    # Create runner with credential service
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,  # This enables OAuth2 auth
        app_name="github_integration_app"
    )
    
    return runner

# Usage
runner = await setup_github_integration()
'''
    print(integration_code)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_integration_pattern())