"""AdkBuilder Usage Examples.

This module demonstrates various usage patterns for the AdkBuilder class,
which provides an enhanced way to configure Google ADK applications with
custom credential services and other advanced features.
"""

import asyncio
import tempfile
import os
from pathlib import Path

from google_adk_extras.adk_builder import AdkBuilder
from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
from google_adk_extras.credentials.http_basic_auth_credential_service import HTTPBasicAuthCredentialService
from google_adk_extras.credentials.google_oauth2_credential_service import GoogleOAuth2CredentialService


def create_sample_agent_directory():
    """Create a sample agent directory for examples."""
    temp_dir = tempfile.mkdtemp(prefix="adk_examples_")
    agents_dir = os.path.join(temp_dir, "agents")
    os.makedirs(agents_dir, exist_ok=True)
    
    # Create a sample agent
    sample_agent_dir = os.path.join(agents_dir, "sample_agent")
    os.makedirs(sample_agent_dir, exist_ok=True)
    
    # Create root_agent.yaml
    agent_config = """
name: Sample Agent
instructions: |
  You are a helpful AI assistant that can help users with various tasks.
  You have access to custom credential services for authentication.
  
model:
  provider: "openai"
  name: "gpt-4"
  
tools: []
"""
    
    with open(os.path.join(sample_agent_dir, "root_agent.yaml"), "w") as f:
        f.write(agent_config)
    
    return agents_dir


def example_1_basic_usage():
    """Example 1: Basic AdkBuilder usage with minimal configuration."""
    print("=== Example 1: Basic Usage ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Create a basic AdkBuilder configuration
        builder = AdkBuilder()
        app = builder.with_agents_dir(agents_dir).build_fastapi_app()
        
        print(f"✓ Created FastAPI app with agents from: {agents_dir}")
        print("  - Uses default InMemoryCredentialService")
        print("  - Web UI enabled")
        print("  - Default host: 127.0.0.1:8000")
        
    finally:
        # Clean up
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_2_jwt_credentials():
    """Example 2: Using JWT credential service with URI configuration."""
    print("\n=== Example 2: JWT Credentials via URI ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Configure JWT credentials using URI
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(agents_dir)
               .with_credential_service_uri("jwt://my-secret-key@algorithm=HS256&issuer=my-app&expiry=3600")
               .build_fastapi_app())
        
        print("✓ Created FastAPI app with JWT credential service")
        print("  - Secret: 'my-secret-key'")
        print("  - Algorithm: HS256")
        print("  - Issuer: 'my-app'")
        print("  - Token expiry: 3600 seconds")
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_3_instance_based_credentials():
    """Example 3: Using credential service instances."""
    print("\n=== Example 3: Instance-based Credentials ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Create credential service instance
        jwt_service = JWTCredentialService(
            secret="instance-secret",
            algorithm="HS256",
            issuer="example-app",
            token_expiry=7200
        )
        
        # Configure with service instance
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(agents_dir)
               .with_credential_service(jwt_service)
               .build_fastapi_app())
        
        print("✓ Created FastAPI app with JWT service instance")
        print("  - Configured programmatically")
        print("  - Custom token expiry: 7200 seconds")
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_4_basic_auth_credentials():
    """Example 4: HTTP Basic Authentication."""
    print("\n=== Example 4: HTTP Basic Authentication ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Configure Basic Auth using URI
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(agents_dir)
               .with_credential_service_uri("basic-auth://admin:secure-password")
               .build_fastapi_app())
        
        print("✓ Created FastAPI app with HTTP Basic Auth")
        print("  - Username: 'admin'")
        print("  - Password: 'secure-password'")
        print("  - Supports base64 encoded credentials")
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_5_oauth2_google():
    """Example 5: Google OAuth2 configuration."""
    print("\n=== Example 5: Google OAuth2 (Configuration Only) ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Configure Google OAuth2 (for demonstration - requires real credentials in production)
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(agents_dir)
               .with_credential_service_uri("oauth2-google://demo-client-id:demo-secret@scopes=openid,calendar,gmail.readonly")
               .build_fastapi_app())
        
        print("✓ Created FastAPI app with Google OAuth2 configuration")
        print("  - Client ID: 'demo-client-id'")
        print("  - Scopes: openid, calendar, gmail.readonly")
        print("  - Note: This is for demonstration - use real credentials in production")
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_6_comprehensive_configuration():
    """Example 6: Comprehensive configuration with multiple services."""
    print("\n=== Example 6: Comprehensive Configuration ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Create a database file for session storage
        db_path = os.path.join(tempfile.gettempdir(), "adk_example_sessions.db")
        
        # Comprehensive configuration
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(agents_dir)
               .with_session_service(f"sqlite:///{db_path}", echo=False, pool_pre_ping=True)
               .with_credential_service_uri("jwt://comprehensive-secret@algorithm=HS256&issuer=comprehensive-app")
               .with_cors(["http://localhost:3000", "https://app.example.com"])
               .with_web_ui(True)
               .with_a2a_protocol(False)
               .with_host_port("0.0.0.0", 8080)
               .with_cloud_tracing(False)  # Disabled for example
               .with_agent_reload(True)
               .build_fastapi_app())
        
        print("✓ Created FastAPI app with comprehensive configuration")
        print(f"  - Session storage: SQLite database at {db_path}")
        print("  - JWT credentials with custom issuer")
        print("  - CORS enabled for specific origins")
        print("  - Web UI enabled")
        print("  - A2A protocol disabled")
        print("  - Host: 0.0.0.0:8080")
        print("  - Agent hot reloading enabled")
        
        # Clean up database
        if os.path.exists(db_path):
            os.remove(db_path)
            
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_7_fluent_interface():
    """Example 7: Demonstrating fluent interface patterns."""
    print("\n=== Example 7: Fluent Interface Patterns ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Demonstrate method chaining
        app = (AdkBuilder()
               .with_agents_dir(agents_dir)
               .with_credential_service_uri("basic-auth://fluent:interface")
               .with_web_ui(True)
               .with_host_port("127.0.0.1", 8000)
               .build_fastapi_app())
        
        print("✓ Created FastAPI app using fluent interface")
        print("  - All configuration in a single chain")
        print("  - Clean, readable configuration")
        print("  - Method chaining for concise setup")
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_8_lifespan_configuration():
    """Example 8: Custom lifespan configuration."""
    print("\n=== Example 8: Custom Lifespan Configuration ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Define custom lifespan
        async def custom_lifespan(app):
            print("🚀 Application starting up...")
            # Startup logic here
            yield
            print("🛑 Application shutting down...")
            # Cleanup logic here
        
        # Configure with custom lifespan
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(agents_dir)
               .with_credential_service_uri("jwt://lifespan-example@issuer=lifespan-app")
               .with_lifespan(custom_lifespan)
               .build_fastapi_app())
        
        print("✓ Created FastAPI app with custom lifespan")
        print("  - Custom startup and shutdown handlers")
        print("  - Integrated with ADK lifecycle")
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def example_9_error_handling():
    """Example 9: Error handling and validation."""
    print("\n=== Example 9: Error Handling ===")
    
    # Example of validation errors
    try:
        builder = AdkBuilder()
        # This will raise ValueError
        app = builder.build_fastapi_app()
    except ValueError as e:
        print(f"✓ Caught expected validation error: {e}")
    
    try:
        builder = AdkBuilder()
        # This will raise ValueError for unsupported URI
        builder.with_credential_service_uri("unsupported://invalid-scheme")
        app = builder.with_agents_dir("/tmp").build_fastapi_app()
    except ValueError as e:
        print(f"✓ Caught expected URI parsing error: {e}")
    
    print("  - Proper validation of configuration")
    print("  - Clear error messages for debugging")


def example_10_production_patterns():
    """Example 10: Production-ready patterns."""
    print("\n=== Example 10: Production Patterns ===")
    
    agents_dir = create_sample_agent_directory()
    
    try:
        # Production-like configuration
        production_builder = (AdkBuilder()
                             .with_agents_dir(agents_dir)
                             .with_session_service("sqlite:///prod_sessions.db")  # Use PostgreSQL in real production
                             .with_credential_service_uri("jwt://prod-secret-key@algorithm=HS256&issuer=production-app&expiry=1800")
                             .with_cors(["https://yourdomain.com", "https://app.yourdomain.com"])
                             .with_web_ui(True)
                             .with_host_port("0.0.0.0", 8000)
                             .with_cloud_tracing(True)  # Enable in production
                             .with_agent_reload(False))  # Disable in production
        
        app = production_builder.build_fastapi_app()
        
        print("✓ Created production-ready FastAPI app")
        print("  - Secure JWT configuration with short expiry")
        print("  - CORS configured for specific domains")
        print("  - Cloud tracing enabled")
        print("  - Agent reloading disabled for stability")
        print("  - Bind to all interfaces for container deployment")
        
        # In production, you would run this with:
        # uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
        
    finally:
        import shutil
        shutil.rmtree(os.path.dirname(agents_dir))


def main():
    """Run all examples."""
    print("AdkBuilder Examples")
    print("===================")
    print("\nThis demonstrates various usage patterns for the AdkBuilder class.")
    print("Each example shows different ways to configure Google ADK applications.")
    
    examples = [
        example_1_basic_usage,
        example_2_jwt_credentials,
        example_3_instance_based_credentials,
        example_4_basic_auth_credentials,
        example_5_oauth2_google,
        example_6_comprehensive_configuration,
        example_7_fluent_interface,
        example_8_lifespan_configuration,
        example_9_error_handling,
        example_10_production_patterns,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"❌ Error in {example.__name__}: {e}")
    
    print("\n=== Examples Complete ===")
    print("\nFor more information:")
    print("- Check the AdkBuilder class documentation")
    print("- Review unit and integration tests")
    print("- See the credential service implementations")


if __name__ == "__main__":
    main()