#!/usr/bin/env python3
"""Example of using JWT credential service."""

import os
import asyncio
from google_adk_extras.credentials import JWTCredentialService


async def main():
    """Demonstrate JWT credential service usage."""
    print("JWT Credential Service Example")
    print("=" * 50)
    
    # Get JWT secret from environment variable
    jwt_secret = os.environ.get("JWT_SECRET")
    
    if not jwt_secret:
        print("Warning: JWT_SECRET environment variable not set")
        print("Using a demo secret for example purposes")
        jwt_secret = "your-super-secret-jwt-signing-key-change-this-in-production"
    
    # Initialize JWT credential service
    credential_service = JWTCredentialService(
        secret=jwt_secret,
        algorithm="HS256",
        issuer="my-app",
        audience="api.example.com",
        expiration_minutes=60,
        custom_claims={
            "role": "user",
            "permissions": ["read", "write"]
        },
        use_session_state=False  # Use in-memory storage for demo
    )
    
    try:
        # Initialize the service
        print("Initializing JWT credential service...")
        await credential_service.initialize()
        print("✓ Service initialized successfully")
        
        # Generate a JWT token for a user
        user_id = "demo_user_123"
        print(f"\nGenerating JWT token for user: {user_id}")
        
        token = credential_service.generate_jwt_token(
            user_id=user_id,
            additional_claims={
                "session_id": "session_abc123",
                "department": "engineering"
            }
        )
        print(f"✓ JWT token generated: {token[:50]}...")
        
        # Verify the token
        print("\nVerifying JWT token...")
        try:
            payload = credential_service.verify_jwt_token(token)
            print("✓ Token is valid")
            print(f"  Subject (user): {payload['sub']}")
            print(f"  Issuer: {payload.get('iss', 'N/A')}")
            print(f"  Audience: {payload.get('aud', 'N/A')}")
            print(f"  Role: {payload.get('role', 'N/A')}")
            print(f"  Permissions: {payload.get('permissions', 'N/A')}")
            print(f"  Session ID: {payload.get('session_id', 'N/A')}")
            print(f"  Department: {payload.get('department', 'N/A')}")
        except Exception as e:
            print(f"✗ Token verification failed: {e}")
        
        # Check token expiration
        print("\nChecking token expiration...")
        is_expired = credential_service.is_token_expired(token)
        print(f"  Token expired: {is_expired}")
        
        # Get token information
        print("\nGetting token information...")
        token_info = credential_service.get_token_info(token)
        if "error" not in token_info:
            print(f"  Expires at: {token_info.get('expires_at', 'N/A')}")
            print(f"  Expired: {token_info.get('expired', 'N/A')}")
        
        # Create auth configuration
        print("\nCreating authentication configuration...")
        auth_config = credential_service.create_auth_config(user_id)
        print("✓ Auth config created")
        
        # Display credential information
        raw_credential = auth_config.raw_auth_credential
        print(f"\nCredential Configuration:")
        print(f"  Auth Type: {raw_credential.auth_type}")
        print(f"  HTTP Scheme: {raw_credential.http.scheme}")
        print(f"  Bearer Token: {raw_credential.http.credentials.token[:50]}...")
        
        print("\n📝 Note: This example demonstrates JWT token generation and validation.")
        print("   In a real application, you would integrate this with Google ADK's")
        print("   Runner and Agent for automatic token-based authentication.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await credential_service.cleanup()
        print("\n✓ Service cleaned up")


async def demonstrate_token_refresh():
    """Show JWT token automatic refresh capability."""
    print("\n" + "=" * 60)
    print("JWT Token Automatic Refresh Example")
    print("=" * 60)
    
    # Create service with very short expiration for demo
    credential_service = JWTCredentialService(
        secret="demo-secret-key",
        expiration_minutes=1,  # 1 minute for demo
        use_session_state=False
    )
    
    try:
        await credential_service.initialize()
        
        user_id = "refresh_demo_user"
        print(f"Creating JWT with 1-minute expiration for user: {user_id}")
        
        # Generate token
        token1 = credential_service.generate_jwt_token(user_id)
        print(f"Initial token: {token1[:30]}...")
        
        # Wait a moment
        print("Waiting 2 seconds...")
        await asyncio.sleep(2)
        
        # Generate another token (should be different due to timestamp)
        token2 = credential_service.generate_jwt_token(user_id)
        print(f"New token:     {token2[:30]}...")
        print(f"Tokens are different: {token1 != token2}")
        
        print("\nIn a real application with longer expiration times,")
        print("the load_credential method would automatically refresh")
        print("expired tokens before returning them to the application.")
        
    finally:
        await credential_service.cleanup()


async def demonstrate_integration_pattern():
    """Show how to integrate with Google ADK Runner."""
    print("\n" + "=" * 60)
    print("Google ADK Integration Pattern")
    print("=" * 60)
    
    integration_code = '''
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService  
from google_adk_extras.credentials import JWTCredentialService

async def setup_jwt_integration():
    """Setup JWT authentication with ADK Runner."""
    
    # Initialize credential service
    credential_service = JWTCredentialService(
        secret=os.environ["JWT_SECRET"],
        algorithm="HS256",
        issuer="my-app",
        audience="api.example.com",
        expiration_minutes=120,
        custom_claims={
            "role": "api_user",
            "permissions": ["read", "write", "admin"]
        }
    )
    await credential_service.initialize()
    
    # Setup other services
    session_service = InMemorySessionService()
    
    # Create agent with tools that require JWT authentication
    agent = Agent(
        name="jwt_protected_assistant",
        model="gemini-2.0-flash",
        instruction="You can access protected APIs using JWT tokens.",
        tools=[]  # Add API tools that require JWT authentication
    )
    
    # Create runner with credential service
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,  # This enables JWT auth
        app_name="jwt_integration_app"
    )
    
    return runner

# Usage
runner = await setup_jwt_integration()
'''
    print(integration_code)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_token_refresh())
    asyncio.run(demonstrate_integration_pattern())