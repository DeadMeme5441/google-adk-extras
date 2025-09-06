#!/usr/bin/env python3
"""Example of using X (Twitter) OAuth2 credential service."""

import os
import asyncio
from google_adk_extras.credentials import XOAuth2CredentialService


async def main():
    """Demonstrate X OAuth2 credential service usage."""
    print("X (Twitter) OAuth2 Credential Service Example")
    print("=" * 50)
    
    # Get credentials from environment variables
    client_id = os.environ.get("X_CLIENT_ID")
    client_secret = os.environ.get("X_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: Please set X_CLIENT_ID and X_CLIENT_SECRET environment variables")
        print("\nTo get these credentials:")
        print("1. Go to https://developer.twitter.com/")
        print("2. Create a Twitter Developer account")
        print("3. Create a new App in the Developer Portal")
        print("4. Enable OAuth 2.0 in App settings")
        print("5. Configure redirect URIs")
        print("6. Get Client ID and Client Secret from Keys and Tokens")
        return
    
    # Initialize X OAuth2 credential service
    credential_service = XOAuth2CredentialService(
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "tweet.read",        # Read tweets
            "tweet.write",       # Write tweets
            "users.read",        # Read user information
            "follows.read",      # Read follows
            "follows.write",     # Manage follows
            "like.read",         # Read likes
            "like.write",        # Manage likes
            "offline.access"     # Maintain access when offline
        ],
        use_session_state=False  # Use in-memory storage for demo
    )
    
    try:
        # Initialize the service
        print("Initializing X OAuth2 credential service...")
        await credential_service.initialize()
        print("✓ Service initialized successfully")
        
        # Display supported scopes
        print("\nSupported X OAuth2 scopes:")
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
        print("1. User would be redirected to X authorization URL")
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


async def demonstrate_scope_categories():
    """Show different X API scope categories."""
    print("\n" + "=" * 60)
    print("X API v2 Scope Categories")
    print("=" * 60)
    
    scope_categories = {
        "Tweet Operations": [
            ("tweet.read", "Read tweets"),
            ("tweet.write", "Write tweets"),
            ("tweet.moderate.write", "Hide and unhide replies to your tweets")
        ],
        "User Operations": [
            ("users.read", "Read user profile information")
        ],
        "Social Operations": [
            ("follows.read", "Read who a user is following"),
            ("follows.write", "Follow and unfollow other users"),
            ("like.read", "Read liked tweets"),
            ("like.write", "Like and unlike tweets"),
            ("mute.read", "Read muted accounts"),
            ("mute.write", "Mute and unmute accounts"),
            ("block.read", "Read blocked accounts"),
            ("block.write", "Block and unblock accounts")
        ],
        "Content Operations": [
            ("list.read", "Read list information"),
            ("list.write", "Create and manage lists"),
            ("bookmark.read", "Read bookmarked tweets"),
            ("bookmark.write", "Bookmark and unbookmark tweets")
        ],
        "Advanced Features": [
            ("space.read", "Read Spaces information"),
            ("dm.read", "Read direct messages"),
            ("dm.write", "Send direct messages"),
            ("offline.access", "Maintain access when users are offline")
        ]
    }
    
    for category, scopes in scope_categories.items():
        print(f"\n{category}:")
        for scope, description in scopes:
            print(f"  {scope:<25} - {description}")


async def demonstrate_integration_pattern():
    """Show how to integrate with Google ADK Runner."""
    print("\n" + "=" * 60)
    print("Google ADK Integration Pattern")
    print("=" * 60)
    
    integration_code = '''
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService  
from google_adk_extras.credentials import XOAuth2CredentialService

async def setup_x_integration():
    """Setup X OAuth2 with ADK Runner."""
    
    # Initialize credential service
    credential_service = XOAuth2CredentialService(
        client_id=os.environ["X_CLIENT_ID"],
        client_secret=os.environ["X_CLIENT_SECRET"],
        scopes=["tweet.read", "tweet.write", "users.read", "offline.access"]
    )
    await credential_service.initialize()
    
    # Setup other services
    session_service = InMemorySessionService()
    
    # Create agent with tools that require X API v2
    agent = Agent(
        name="x_assistant",
        model="gemini-2.0-flash",
        instruction="You can read and post tweets on behalf of users.",
        tools=[]  # Add X API tools here
    )
    
    # Create runner with credential service
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,  # This enables OAuth2 auth
        app_name="x_integration_app"
    )
    
    return runner

# Usage
runner = await setup_x_integration()
'''
    print(integration_code)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_scope_categories())
    asyncio.run(demonstrate_integration_pattern())