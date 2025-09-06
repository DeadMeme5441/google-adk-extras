#!/usr/bin/env python3
"""Example of using HTTP Basic Auth credential service."""

import os
import asyncio
from google_adk_extras.credentials import HTTPBasicAuthCredentialService, HTTPBasicAuthWithCredentialsService


async def main():
    """Demonstrate HTTP Basic Auth credential service usage."""
    print("HTTP Basic Auth Credential Service Example")
    print("=" * 50)
    
    # Get credentials from environment variables
    username = os.environ.get("API_USERNAME", "demo_user")
    password = os.environ.get("API_PASSWORD", "demo_password")
    
    if username == "demo_user" or password == "demo_password":
        print("Warning: Using demo credentials")
        print("Set API_USERNAME and API_PASSWORD environment variables for real usage")
    
    # Initialize HTTP Basic Auth credential service
    credential_service = HTTPBasicAuthCredentialService(
        username=username,
        password=password,
        realm="API Access",
        use_session_state=False  # Use in-memory storage for demo
    )
    
    try:
        # Initialize the service
        print("Initializing HTTP Basic Auth credential service...")
        await credential_service.initialize()
        print("✓ Service initialized successfully")
        
        # Get credential information (without exposing password)
        print("\nCredential Information:")
        cred_info = credential_service.get_credential_info()
        for key, value in cred_info.items():
            print(f"  {key}: {value}")
        
        # Generate Authorization header
        print("\nGenerating Authorization header...")
        auth_header = credential_service.get_auth_header()
        print(f"  Authorization: {auth_header}")
        
        # Decode the header back to verify
        print("\nDecoding Authorization header...")
        try:
            decoded_username, decoded_password = credential_service.decode_basic_auth(auth_header)
            print(f"  Decoded username: {decoded_username}")
            print(f"  Decoded password: {'*' * len(decoded_password)}")
        except Exception as e:
            print(f"  Decoding error: {e}")
        
        # Validate credentials
        print("\nValidating credentials...")
        is_valid = credential_service.validate_credentials(username, password)
        print(f"  Valid credentials: {is_valid}")
        
        # Test with wrong credentials
        is_invalid = credential_service.validate_credentials("wrong_user", password)
        print(f"  Wrong credentials: {is_invalid}")
        
        # Create auth configuration
        print("\nCreating authentication configuration...")
        auth_config = credential_service.create_auth_config()
        print("✓ Auth config created")
        
        # Display credential information
        raw_credential = auth_config.raw_auth_credential
        print(f"\nCredential Configuration:")
        print(f"  Auth Type: {raw_credential.auth_type}")
        print(f"  HTTP Scheme: {raw_credential.http.scheme}")
        print(f"  Username: {raw_credential.http.credentials.username}")
        print(f"  Password: {'*' * len(raw_credential.http.credentials.password)}")
        
        print("\n📝 Note: This example demonstrates HTTP Basic Auth setup.")
        print("   In a real application, you would integrate this with Google ADK's")
        print("   Runner and Agent for automatic Basic Auth header injection.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await credential_service.cleanup()
        print("\n✓ Service cleaned up")


async def demonstrate_multi_credential_service():
    """Show HTTPBasicAuthWithCredentialsService with multiple users."""
    print("\n" + "=" * 60)
    print("HTTP Basic Auth Multi-Credential Service Example")
    print("=" * 60)
    
    # Initialize service with multiple credential pairs
    credential_service = HTTPBasicAuthWithCredentialsService(
        credentials={
            "admin": "admin_password",
            "user1": "user1_password", 
            "api_client": "api_secret_key",
            "readonly": "readonly_pass"
        },
        default_username="api_client",
        realm="Multi-User API",
        use_session_state=False
    )
    
    try:
        await credential_service.initialize()
        print("✓ Multi-credential service initialized")
        
        # Show available usernames
        print("\nAvailable usernames:")
        usernames = credential_service.get_available_usernames()
        for username in usernames:
            print(f"  - {username}")
        
        # Create auth config for default user
        print(f"\nCreating auth config for default user...")
        auth_config = credential_service.create_auth_config()
        print(f"  Default user: {auth_config.raw_auth_credential.http.credentials.username}")
        
        # Create auth config for specific user
        print(f"\nCreating auth config for specific user 'admin'...")
        admin_auth_config = credential_service.create_auth_config("admin")
        print(f"  Specific user: {admin_auth_config.raw_auth_credential.http.credentials.username}")
        
        # Try invalid user
        print(f"\nTrying invalid user 'nonexistent'...")
        try:
            invalid_auth_config = credential_service.create_auth_config("nonexistent")
        except ValueError as e:
            print(f"  ✓ Correctly rejected: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
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
from google_adk_extras.credentials import HTTPBasicAuthCredentialService

async def setup_basic_auth_integration():
    """Setup HTTP Basic Auth with ADK Runner."""
    
    # Initialize credential service
    credential_service = HTTPBasicAuthCredentialService(
        username=os.environ["API_USERNAME"],
        password=os.environ["API_PASSWORD"],
        realm="Protected API"
    )
    await credential_service.initialize()
    
    # Setup other services
    session_service = InMemorySessionService()
    
    # Create agent with tools that require Basic Auth
    agent = Agent(
        name="basic_auth_assistant",
        model="gemini-2.0-flash",
        instruction="You can access protected APIs using HTTP Basic Authentication.",
        tools=[]  # Add API tools that require Basic Auth
    )
    
    # Create runner with credential service
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,  # This enables Basic Auth
        app_name="basic_auth_integration_app"
    )
    
    return runner

# Usage
runner = await setup_basic_auth_integration()

# Example with multiple credentials
async def setup_multi_credential_integration():
    """Setup multi-credential Basic Auth with ADK Runner."""
    
    credential_service = HTTPBasicAuthWithCredentialsService(
        credentials={
            "admin": os.environ["ADMIN_PASSWORD"],
            "user": os.environ["USER_PASSWORD"],
            "readonly": os.environ["READONLY_PASSWORD"]
        },
        default_username="user"  # Default for most operations
    )
    await credential_service.initialize()
    
    # Use with Runner - it will use the default user
    # or can be configured to switch users based on context
    runner = Runner(
        agent=agent,
        session_service=session_service,
        credential_service=credential_service,
        app_name="multi_user_app"
    )
    
    return runner
'''
    print(integration_code)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_multi_credential_service())
    asyncio.run(demonstrate_integration_pattern())