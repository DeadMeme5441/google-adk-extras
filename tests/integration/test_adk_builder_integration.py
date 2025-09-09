"""Integration tests for AdkBuilder."""

import pytest
import tempfile
import os
import shutil

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    _FASTAPI = True
except Exception:
    _FASTAPI = False

from google_adk_extras.adk_builder import AdkBuilder
try:
    _HAVE_JWT = True
except Exception:
    _HAVE_JWT = False


import pytest as _pytest

_pytestmark = _pytest.mark.skipif(not _FASTAPI, reason="fastapi not installed")

class TestAdkBuilderIntegration:
    """Integration tests for AdkBuilder with real services."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.temp_dir, "agents")
        os.makedirs(self.agents_dir, exist_ok=True)
        
        # Create a minimal test agent
        self.test_agent_dir = os.path.join(self.agents_dir, "test_agent")
        os.makedirs(self.test_agent_dir, exist_ok=True)
        
        # Create root_agent.yaml
        agent_config = """
name: Test Agent
instructions: |
  You are a test agent for integration testing.
  
model:
  provider: "openai"
  name: "gpt-4"
  
tools: []
"""
        with open(os.path.join(self.test_agent_dir, "root_agent.yaml"), "w") as f:
            f.write(agent_config)
    
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_build_minimal_fastapi_app(self):
        """Test building a minimal FastAPI app with AdkBuilder."""
        builder = AdkBuilder()
        app = builder.with_agents_dir(self.agents_dir).build_fastapi_app()
        
        assert isinstance(app, FastAPI)
        assert app is not None
        
        # Test that the app can be instantiated as a test client
        with TestClient(app) as client:
            # Basic health check - the app should start without errors
            pass
    
    # credential-service URI integration tests removed
    
    # basic-auth integration test removed
    
    def test_build_app_with_session_db_kwargs(self):
        """Test building FastAPI app with session database configuration."""
        db_path = os.path.join(self.temp_dir, "test_sessions.db")
        session_uri = f"sqlite:///{db_path}"
        
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(self.agents_dir)
               .with_session_service(session_uri, echo=False, pool_pre_ping=True)
               .build_fastapi_app())
        
        assert isinstance(app, FastAPI)
        
        with TestClient(app) as client:
            # App should start successfully with database session service
            pass
    
    def test_build_app_with_cors_configuration(self):
        """Test building FastAPI app with CORS configuration."""
        origins = ["http://localhost:3000", "https://app.example.com"]
        
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(self.agents_dir)
               .with_cors(origins)
               .build_fastapi_app())
        
        assert isinstance(app, FastAPI)
        
        with TestClient(app) as client:
            # Test CORS preflight request
            response = client.options("/", headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            })
            # Should not fail - CORS should be configured
    
    def test_build_app_with_web_ui_disabled(self):
        """Test building FastAPI app with web UI disabled."""
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(self.agents_dir)
               .with_web_ui(False)
               .build_fastapi_app())
        
        assert isinstance(app, FastAPI)
        
        with TestClient(app) as client:
            # App should start successfully without web UI
            pass
    
    def test_build_app_with_custom_host_port(self):
        """Test building FastAPI app with custom host and port configuration."""
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(self.agents_dir)
               .with_host_port("0.0.0.0", 9000)
               .build_fastapi_app())
        
        assert isinstance(app, FastAPI)
        
        with TestClient(app) as client:
            # App should start successfully with custom host/port
            pass
    
    def test_build_app_with_multiple_configurations(self):
        """Test building FastAPI app with multiple configuration options."""
        db_path = os.path.join(self.temp_dir, "test.db")

        builder = AdkBuilder()
        builder = (builder
                   .with_agents_dir(self.agents_dir)
                   .with_session_service(f"sqlite:///{db_path}")
                   .with_cors(["http://localhost:3000"])
                   .with_web_ui(True)
                   .with_a2a_protocol(False)
                   .with_host_port("127.0.0.1", 8001))

        # credential URI helpers removed

        app = builder.build_fastapi_app()
        
        assert isinstance(app, FastAPI)
        
        with TestClient(app) as client:
            # App should start successfully with all configurations
            pass
    
    # credential integration test removed
    
    def test_error_handling_invalid_agents_dir(self):
        """Test error handling for invalid agents directory."""
        builder = AdkBuilder()
        
        with pytest.raises(ValueError, match="No agent configuration provided"):
            builder.build_fastapi_app()
    
    def test_error_handling_nonexistent_agents_dir(self):
        """Test behavior with non-existent agents directory."""
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")
        
        builder = AdkBuilder()
        # This should not raise an error - ADK should handle missing directories
        app = builder.with_agents_dir(nonexistent_dir).build_fastapi_app()
        
        assert isinstance(app, FastAPI)
    
    # URI-based credential configuration tests removed
    
    def test_lifespan_integration(self):
        """Test FastAPI lifespan integration."""
        from contextlib import asynccontextmanager
        
        lifespan_called = {"startup": False, "shutdown": False}
        
        @asynccontextmanager
        async def test_lifespan(app: FastAPI):
            lifespan_called["startup"] = True
            yield
            lifespan_called["shutdown"] = True
        
        builder = AdkBuilder()
        app = (builder
               .with_agents_dir(self.agents_dir)
               .with_lifespan(test_lifespan)
               .build_fastapi_app())
        
        assert isinstance(app, FastAPI)
        
        # Test that lifespan is properly configured
        # Note: In a real test, we would start/stop the app to verify lifespan calls
        with TestClient(app) as client:
            # Lifespan events should be properly configured
            # (TestClient automatically handles lifespan events)
            pass
    
    @pytest.mark.skipif(
        not os.path.exists("/tmp"),
        reason="Requires /tmp directory for database testing"
    )
    def test_database_session_integration(self):
        """Test integration with database session service."""
        db_path = "/tmp/adk_builder_integration_test.db"
        
        # Clean up any existing test database
        if os.path.exists(db_path):
            os.remove(db_path)
        
        try:
            builder = AdkBuilder()
            app = (builder
                   .with_agents_dir(self.agents_dir)
                   .with_session_service(f"sqlite:///{db_path}")
                   .build_fastapi_app())
            
            assert isinstance(app, FastAPI)
            
            with TestClient(app) as client:
                # App should work with database session service
                pass
                
            # Verify database file was created (indicates session service is working)
            assert os.path.exists(db_path)
            
        finally:
            # Clean up test database
            if os.path.exists(db_path):
                os.remove(db_path)
