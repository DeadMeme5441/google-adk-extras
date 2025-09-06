"""Unit tests for AdkBuilder."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from starlette.types import Lifespan

from fastapi import FastAPI

from google_adk_extras.adk_builder import AdkBuilder
from google_adk_extras.credentials.google_oauth2_credential_service import GoogleOAuth2CredentialService
from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
from google_adk_extras.credentials.http_basic_auth_credential_service import HTTPBasicAuthCredentialService
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
    
    def test_credential_service_instance(self):
        """Test credential service instance configuration."""
        cred_service = GoogleOAuth2CredentialService("client-id", "client-secret")
        builder = AdkBuilder()
        builder.with_credential_service(cred_service)
        
        assert builder._credential_service is cred_service
    
    def test_credential_service_oauth2_google_uri_parsing(self):
        """Test OAuth2 Google URI parsing."""
        builder = AdkBuilder()
        builder.with_credential_service_uri("oauth2-google://client-id:secret@scopes=calendar,gmail.readonly")
        
        credential_service = builder._create_credential_service()
        assert isinstance(credential_service, GoogleOAuth2CredentialService)
        assert credential_service.client_id == "client-id"
        assert credential_service.client_secret == "secret"
        assert "calendar" in credential_service.scopes
        assert "gmail.readonly" in credential_service.scopes
    
    def test_credential_service_jwt_uri_parsing(self):
        """Test JWT URI parsing."""
        builder = AdkBuilder()
        builder.with_credential_service_uri("jwt://my-secret@algorithm=HS256&issuer=test-app")
        
        credential_service = builder._create_credential_service()
        assert isinstance(credential_service, JWTCredentialService)
        assert credential_service.secret == "my-secret"
        assert credential_service.algorithm == "HS256"
        assert credential_service.issuer == "test-app"
    
    def test_credential_service_basic_uri_parsing(self):
        """Test HTTP Basic Auth URI parsing."""
        builder = AdkBuilder()
        builder.with_credential_service_uri("basic-auth://username:password")
        
        credential_service = builder._create_credential_service()
        assert isinstance(credential_service, HTTPBasicAuthCredentialService)
        assert credential_service.default_username == "username"
        assert credential_service.default_password == "password"
    
    def test_credential_service_uri_parsing_invalid(self):
        """Test invalid credential service URI handling."""
        builder = AdkBuilder()
        
        with pytest.raises(ValueError, match="Unsupported credential service URI"):
            builder.with_credential_service_uri("invalid://test")
    
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
        
        with pytest.raises(ValueError, match="agents_dir is required"):
            builder.build_fastapi_app()
    
    @patch('google_adk_extras.adk_builder.get_enhanced_fast_api_app')
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
    
    @patch('google_adk_extras.adk_builder.get_enhanced_fast_api_app')
    def test_build_fastapi_app_with_custom_credential_service(self, mock_enhanced_app):
        """Test building FastAPI app with custom credential service."""
        mock_app = MagicMock(spec=FastAPI)
        mock_enhanced_app.return_value = mock_app
        
        cred_service = GoogleOAuth2CredentialService("test-id", "test-secret")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = (AdkBuilder()
                      .with_agents_dir(temp_dir)
                      .with_credential_service(cred_service))
            
            result = builder.build_fastapi_app()
            
            # Verify credential service was passed
            call_kwargs = mock_enhanced_app.call_args[1]
            assert call_kwargs['credential_service'] is cred_service
    
    @patch('google_adk_extras.adk_builder.get_enhanced_fast_api_app')
    def test_build_fastapi_app_with_all_options(self, mock_enhanced_app):
        """Test building FastAPI app with all configuration options."""
        mock_app = MagicMock(spec=FastAPI)
        mock_enhanced_app.return_value = mock_app
        
        async def test_lifespan(app: FastAPI):
            yield
        
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = (AdkBuilder()
                      .with_agents_dir(temp_dir)
                      .with_session_service("sqlite:///test.db")
                      .with_artifact_service("gs://test-bucket")
                      .with_memory_service("rag://test-corpus")
                      .with_credential_service_uri("jwt://secret@issuer=test")
                      .with_eval_storage("gs://eval-bucket")
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
            assert call_kwargs['artifact_service_uri'] == "gs://test-bucket"
            assert call_kwargs['memory_service_uri'] == "rag://test-corpus"
            assert call_kwargs['eval_storage_uri'] == "gs://eval-bucket"
            assert call_kwargs['allow_origins'] == ["http://localhost:3000"]
            assert call_kwargs['web'] is True
            assert call_kwargs['a2a'] is False
            assert call_kwargs['host'] == "0.0.0.0"
            assert call_kwargs['port'] == 9000
            assert call_kwargs['trace_to_cloud'] is True
            assert call_kwargs['reload_agents'] is True
            assert call_kwargs['lifespan'] is test_lifespan
            assert 'credential_service' in call_kwargs
    
    @patch('asyncio.run')
    @patch('google_adk_extras.adk_builder.get_enhanced_fast_api_app')
    def test_credential_service_initialization(self, mock_enhanced_app, mock_asyncio_run):
        """Test that custom credential services are properly initialized."""
        mock_app = MagicMock(spec=FastAPI)
        mock_enhanced_app.return_value = mock_app
        
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = (AdkBuilder()
                      .with_agents_dir(temp_dir)
                      .with_credential_service_uri("jwt://secret@issuer=test"))
            
            result = builder.build_fastapi_app()
            
            # Verify credential service initialization was attempted
            # (asyncio.run would be called for initialization)
            mock_asyncio_run.assert_called_once()


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
        builder = AdkBuilder().with_session_service(session_service)
        
        service = builder._create_session_service()
        assert service is session_service
    
    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project', 'GOOGLE_CLOUD_LOCATION': 'us-central1'})
    def test_create_session_service_agentengine_uri(self):
        """Test session service creation from agent engine URI."""
        builder = AdkBuilder().with_session_service("agentengine://12345")
        
        with patch('google.adk.sessions.vertex_ai_session_service.VertexAiSessionService') as mock_service:
            service = builder._create_session_service()
            
            mock_service.assert_called_once_with(
                project="test-project",
                location="us-central1",
                agent_engine_id="12345"
            )
    
    def test_create_artifact_service_default(self):
        """Test default artifact service creation."""
        builder = AdkBuilder()
        service = builder._create_artifact_service()
        
        assert isinstance(service, InMemoryArtifactService)
    
    def test_create_artifact_service_gcs_uri(self):
        """Test artifact service creation from GCS URI."""
        builder = AdkBuilder().with_artifact_service("gs://test-bucket")
        
        with patch('google.adk.artifacts.gcs_artifact_service.GcsArtifactService') as mock_service:
            service = builder._create_artifact_service()
            
            mock_service.assert_called_once_with(bucket_name="test-bucket")
    
    def test_create_memory_service_default(self):
        """Test default memory service creation."""
        builder = AdkBuilder()
        service = builder._create_memory_service()
        
        assert isinstance(service, InMemoryMemoryService)
    
    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project', 'GOOGLE_CLOUD_LOCATION': 'us-central1'})
    def test_create_memory_service_rag_uri(self):
        """Test memory service creation from RAG URI."""
        builder = AdkBuilder().with_memory_service_uri("rag://test-corpus")
        
        with patch('google_adk_extras.adk_builder.VertexAiRagMemoryService') as mock_service:
            service = builder._create_memory_service()
            
            mock_service.assert_called_once_with(
                rag_corpus="projects/test-project/locations/us-central1/ragCorpora/test-corpus"
            )