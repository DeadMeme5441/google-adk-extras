"""Unit tests for AdkBuilder."""

import pytest
import tempfile
from unittest.mock import patch, MagicMock

from fastapi import FastAPI

from google_adk_extras.adk_builder import AdkBuilder
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService


class TestAdkBuilder:
    """Test cases for AdkBuilder class."""
    
    def test_builder_initialization(self):
        """Test AdkBuilder can be instantiated."""
        builder = AdkBuilder()
        assert builder is not None
    
    def test_fluent_interface_agents_dir(self):
        """Test fluent interface for setting agents directory."""
        builder = AdkBuilder()
        result = builder.with_agents_dir("/test/agents")
        
        assert result is builder  # Should return self for chaining
        assert builder._agents_dir == "/test/agents"
    
    def test_fluent_interface_chaining(self):
        """Test that fluent interface allows method chaining."""
        builder = (AdkBuilder()
                  .with_agents_dir("/test/agents")
                  .with_web_ui(True)
                  .with_a2a_protocol(False)
                  .with_host_port("0.0.0.0", 9000))
        
        assert builder._agents_dir == "/test/agents"
        assert builder._web_ui is True
        assert builder._a2a is False
        assert builder._host == "0.0.0.0"
        assert builder._port == 9000
    
    def test_session_service_uri_parsing(self):
        """Test session service URI configuration."""
        builder = AdkBuilder()
        builder.with_session_service("sqlite:///test.db")
        
        assert builder._session_service_uri == "sqlite:///test.db"
    
    def test_session_service_instance(self):
        """Test session service instance configuration."""
        session_service = InMemorySessionService()
        builder = AdkBuilder()
        builder.with_session_service_instance(session_service)
        
        assert builder._session_service is session_service
    
    def test_artifact_service_configuration(self):
        """Test artifact service configuration."""
        artifact_service = InMemoryArtifactService()
        builder = AdkBuilder()
        builder.with_artifact_service_instance(artifact_service)
        builder.with_artifact_service("gs://test-bucket")
        
        assert builder._artifact_service is artifact_service
        assert builder._artifact_service_uri == "gs://test-bucket"
    
    def test_memory_service_configuration(self):
        """Test memory service configuration."""
        memory_service = InMemoryMemoryService()
        builder = AdkBuilder()
        builder.with_memory_service_instance(memory_service)
        builder.with_memory_service("rag://test-corpus")
        
        assert builder._memory_service is memory_service
        assert builder._memory_service_uri == "rag://test-corpus"
    
    # credential service instance tests removed
    
    # OAuth2 Google URI parsing test removed
    
    # JWT credential URI tests removed
    # Basic auth credential URI tests removed
    # Invalid credential URI tests removed
    
    def test_cors_configuration(self):
        """Test CORS origins configuration."""
        origins = ["http://localhost:3000", "https://app.example.com"]
        builder = AdkBuilder()
        builder.with_cors(origins)
        
        assert builder._allow_origins == origins
    
    def test_optional_features_configuration(self):
        """Test optional features configuration."""
        builder = (AdkBuilder()
                  .with_cloud_tracing(True)
                  .with_agent_reload(True)
                  .with_eval_storage("gs://eval-bucket"))
        
        assert builder._trace_to_cloud is True
        assert builder._reload_agents is True
        assert builder._eval_storage_uri == "gs://eval-bucket"
    
    def test_lifespan_configuration(self):
        """Test FastAPI lifespan configuration."""
        async def test_lifespan(app: FastAPI):
            yield
        
        builder = AdkBuilder()
        builder.with_lifespan(test_lifespan)
        
        assert builder._lifespan is test_lifespan
    
    def test_build_fastapi_app_requires_agents_dir(self):
        """Test that building FastAPI app requires agents directory."""
        builder = AdkBuilder()
        
        with pytest.raises(ValueError, match="No agent configuration provided"):
            builder.build_fastapi_app()
    
    @patch('google_adk_extras.enhanced_fastapi.get_enhanced_fast_api_app')
    def test_build_fastapi_app_calls_enhanced_function(self, mock_enhanced_app):
        """Test that build_fastapi_app calls our enhanced function."""
        mock_app = MagicMock(spec=FastAPI)
        mock_enhanced_app.return_value = mock_app
        
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AdkBuilder().with_agents_dir(temp_dir)
            result = builder.build_fastapi_app()
            
            # Verify our enhanced function was called
            mock_enhanced_app.assert_called_once()
            call_kwargs = mock_enhanced_app.call_args[1]
            assert call_kwargs['agents_dir'] == temp_dir
            assert 'credential_service' in call_kwargs
            assert result is mock_app
    
    @patch('google_adk_extras.enhanced_fastapi.get_enhanced_fast_api_app')
    def test_build_fastapi_app_with_custom_credential_service(self, mock_enhanced_app):
        """Test building FastAPI app with explicit ADK credential service."""
        from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
        mock_app = MagicMock(spec=FastAPI)
        mock_enhanced_app.return_value = mock_app
        
        cred_service = InMemoryCredentialService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = (AdkBuilder()
                      .with_agents_dir(temp_dir)
                      .with_credential_service(cred_service))
            
            _ = builder.build_fastapi_app()
            
            # Verify credential service was passed
            call_kwargs = mock_enhanced_app.call_args[1]
            assert call_kwargs['credential_service'] is cred_service
    
    @patch('google_adk_extras.enhanced_fastapi.get_enhanced_fast_api_app')
    def test_build_fastapi_app_with_all_options(self, mock_enhanced_app):
        """Test building FastAPI app with all configuration options."""
        try:
            import jwt  # noqa: F401
        except Exception:
            pytest.skip("PyJWT not installed")
        mock_app = MagicMock(spec=FastAPI)
        mock_enhanced_app.return_value = mock_app
        
        async def test_lifespan(app: FastAPI):
            yield
        
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = (AdkBuilder()
                      .with_agents_dir(temp_dir)
                      .with_session_service("sqlite:///test.db")
                      .with_artifact_service("local:///tmp/artifacts")
                      .with_memory_service("yaml:///tmp/memory.yaml")
                      .with_eval_storage("local:///tmp/eval")
                      .with_cors(["http://localhost:3000"])
                      .with_web_ui(True)
                      .with_a2a_protocol(False)
                      .with_host_port("0.0.0.0", 9000)
                      .with_cloud_tracing(True)
                      .with_agent_reload(True)
                      .with_lifespan(test_lifespan))
            
            result = builder.build_fastapi_app()
            
            # Verify all parameters were passed
            call_kwargs = mock_enhanced_app.call_args[1]
            assert call_kwargs['agents_dir'] == temp_dir
            assert call_kwargs['session_service_uri'] == "sqlite:///test.db"
            assert call_kwargs['artifact_service_uri'] == "local:///tmp/artifacts"
            assert call_kwargs['memory_service_uri'] == "yaml:///tmp/memory.yaml"
            assert call_kwargs['eval_storage_uri'] == "local:///tmp/eval"
            assert call_kwargs['allow_origins'] == ["http://localhost:3000"]
            assert call_kwargs['web'] is True
            assert call_kwargs['a2a'] is False
            assert call_kwargs['host'] == "0.0.0.0"
            assert call_kwargs['port'] == 9000
            assert call_kwargs['trace_to_cloud'] is True
            assert call_kwargs['reload_agents'] is True
            assert call_kwargs['lifespan'] is test_lifespan
            assert 'credential_service' in call_kwargs
    
    # credential-service initialization test removed


class TestAdkBuilderServiceCreation:
    """Test cases for service creation methods in AdkBuilder."""
    
    def test_create_session_service_default(self):
        """Test default session service creation."""
        builder = AdkBuilder()
        service = builder._create_session_service()
        
        assert isinstance(service, InMemorySessionService)
    
    def test_create_session_service_instance(self):
        """Test session service creation from instance."""
        session_service = InMemorySessionService()
        builder = AdkBuilder().with_session_service_instance(session_service)
        
        service = builder._create_session_service()
        assert service is session_service
    
    def test_create_session_service_yaml_uri(self):
        """Test session service creation from YAML URI."""
        builder = AdkBuilder().with_session_service("yaml:///path/to/sessions.yaml")
        
        with patch('google_adk_extras.sessions.yaml_file_session_service.YamlFileSessionService') as mock_service:
            service = builder._create_session_service()
            
            mock_service.assert_called_once_with(base_directory="/path/to/sessions.yaml")
    
    def test_create_artifact_service_default(self):
        """Test default artifact service creation."""
        builder = AdkBuilder()
        service = builder._create_artifact_service()
        
        assert isinstance(service, InMemoryArtifactService)
    
    def test_create_artifact_service_local_uri(self):
        """Test artifact service creation from local URI."""
        builder = AdkBuilder().with_artifact_service("local:///path/to/artifacts")
        
        with patch('google_adk_extras.artifacts.local_folder_artifact_service.LocalFolderArtifactService') as mock_service:
            service = builder._create_artifact_service()
            
            mock_service.assert_called_once_with(base_directory="/path/to/artifacts")
    
    def test_create_memory_service_default(self):
        """Test default memory service creation."""
        builder = AdkBuilder()
        service = builder._create_memory_service()
        
        assert isinstance(service, InMemoryMemoryService)
    
    def test_create_memory_service_yaml_uri(self):
        """Test memory service creation from YAML URI."""
        builder = AdkBuilder().with_memory_service("yaml:///path/to/memory.yaml")
        
        with patch('google_adk_extras.memory.yaml_file_memory_service.YamlFileMemoryService') as mock_service:
            service = builder._create_memory_service()
            
            mock_service.assert_called_once_with(base_directory="/path/to/memory.yaml")
