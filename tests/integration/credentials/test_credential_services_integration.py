"""Integration tests for credential services."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from google_adk_extras.credentials import (
    GoogleOAuth2CredentialService,
    GitHubOAuth2CredentialService,
    MicrosoftOAuth2CredentialService,
    XOAuth2CredentialService,
    HTTPBasicAuthCredentialService,
)
try:
    import jwt as _jwt
    from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
    _HAVE_JWT = True
except Exception:
    JWTCredentialService = None  # type: ignore
    _HAVE_JWT = False
from google.adk.auth import AuthConfig
from google.adk.auth.credential_service.base_credential_service import CallbackContext
from google.adk.sessions.session import Session
from google.adk.agents.invocation_context import InvocationContext


class MockCallbackContext:
    """Mock callback context for testing."""
    
    def __init__(self, app_name: str = "test_app", user_id: str = "test_user"):
        self.state = {}
        self._invocation_context = Mock()
        self._invocation_context.app_name = app_name
        self._invocation_context.user_id = user_id


@pytest.mark.asyncio
class TestCredentialServiceIntegration:
    """Integration tests for credential services working together."""

    async def test_google_oauth2_full_workflow(self):
        """Test complete Google OAuth2 workflow."""
        service = GoogleOAuth2CredentialService(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-client-secret",
            scopes=["openid", "calendar", "gmail.readonly"],
            use_session_state=False  # Use in-memory for testing
        )
        
        await service.initialize()
        
        # Create auth config
        auth_config = service.create_auth_config()
        assert auth_config.auth_scheme is not None
        assert auth_config.raw_auth_credential is not None
        
        # Test credential storage workflow
        mock_context = MockCallbackContext()
        
        # Initially no credential stored
        loaded_cred = await service.load_credential(auth_config, mock_context)
        assert loaded_cred is None
        
        # Save a credential
        auth_config.exchanged_auth_credential = auth_config.raw_auth_credential
        await service.save_credential(auth_config, mock_context)
        
        # Load the saved credential
        loaded_cred = await service.load_credential(auth_config, mock_context)
        assert loaded_cred is not None
        assert loaded_cred.oauth2.client_id == "test-client-id.apps.googleusercontent.com"

    async def test_github_oauth2_scope_resolution(self):
        """Test GitHub OAuth2 with various scopes."""
        service = GitHubOAuth2CredentialService(
            client_id="github-client-id",
            client_secret="github-client-secret",
            scopes=["user", "repo", "admin:org", "unknown_scope"],
            use_session_state=False
        )
        
        with patch('google_adk_extras.credentials.github_oauth2_credential_service.logger') as mock_logger:
            await service.initialize()
            # Should log warning about unknown scope
            mock_logger.warning.assert_called_once()
        
        auth_config = service.create_auth_config()
        
        # Verify scopes are properly configured
        oauth_flows = auth_config.auth_scheme.flows
        assert oauth_flows.authorizationCode is not None
        scopes = oauth_flows.authorizationCode.scopes
        assert "user" in scopes
        assert "repo" in scopes
        assert "admin:org" in scopes
        assert "unknown_scope" in scopes

    async def test_microsoft_oauth2_tenant_handling(self):
        """Test Microsoft OAuth2 with different tenant configurations."""
        # Test with common tenant
        service_common = MicrosoftOAuth2CredentialService(
            tenant_id="common",
            client_id="ms-client-id",
            client_secret="ms-client-secret",
            scopes=["User.Read", "Mail.Read"],
            use_session_state=False
        )
        await service_common.initialize()
        
        auth_config_common = service_common.create_auth_config()
        oauth_flows = auth_config_common.auth_scheme.flows
        auth_url = oauth_flows.authorizationCode.authorizationUrl
        token_url = oauth_flows.authorizationCode.tokenUrl
        
        assert "common" in auth_url
        assert "common" in token_url
        assert "v2.0" in auth_url
        assert "v2.0" in token_url
        
        # Test with specific tenant
        service_tenant = MicrosoftOAuth2CredentialService(
            tenant_id="12345-67890-abcdef",
            client_id="ms-client-id",
            client_secret="ms-client-secret",
            use_session_state=False
        )
        await service_tenant.initialize()
        
        auth_config_tenant = service_tenant.create_auth_config()
        oauth_flows_tenant = auth_config_tenant.auth_scheme.flows
        auth_url_tenant = oauth_flows_tenant.authorizationCode.authorizationUrl
        
        assert "12345-67890-abcdef" in auth_url_tenant

    async def test_x_oauth2_configuration(self):
        """Test X (Twitter) OAuth2 configuration."""
        service = XOAuth2CredentialService(
            client_id="x-client-id",
            client_secret="x-client-secret",
            scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
            use_session_state=False
        )
        
        await service.initialize()
        
        auth_config = service.create_auth_config()
        oauth_flows = auth_config.auth_scheme.flows
        
        # Verify X-specific endpoints
        assert "twitter.com" in oauth_flows.authorizationCode.authorizationUrl
        assert "api.twitter.com" in oauth_flows.authorizationCode.tokenUrl
        
        # Verify scopes
        scopes = oauth_flows.authorizationCode.scopes
        assert "tweet.read" in scopes
        assert "tweet.write" in scopes
        assert "users.read" in scopes
        assert "offline.access" in scopes

    async def test_jwt_credential_workflow(self):
        """Test JWT credential service complete workflow."""
        if not _HAVE_JWT:
            pytest.skip("PyJWT not installed")
        service = JWTCredentialService(
            secret="test-jwt-secret-key",
            algorithm="HS256",
            issuer="integration-test",
            audience="test-api",
            expiration_minutes=30,
            custom_claims={"role": "admin", "department": "engineering"},
            use_session_state=False
        )
        
        await service.initialize()
        
        # Generate auth config with token
        user_id = "integration-test-user"
        auth_config = service.create_auth_config(user_id, {"permission": "full"})
        
        assert auth_config.raw_auth_credential.http.scheme == "bearer"
        token = auth_config.raw_auth_credential.http.credentials.token
        assert token is not None
        
        # Verify token contains expected claims
        payload = service.verify_jwt_token(token)
        assert payload["sub"] == user_id
        assert payload["iss"] == "integration-test"
        assert payload["aud"] == "test-api"
        assert payload["role"] == "admin"
        assert payload["department"] == "engineering"
        assert payload["permission"] == "full"
        
        # Test storage workflow
        mock_context = MockCallbackContext(user_id=user_id)
        
        # Save the JWT credential (set exchanged_auth_credential for saving)
        auth_config.exchanged_auth_credential = auth_config.raw_auth_credential
        await service.save_credential(auth_config, mock_context)
        
        # Load and verify it
        loaded_cred = await service.load_credential(auth_config, mock_context)
        assert loaded_cred is not None
        assert loaded_cred.http.credentials.token == token

    async def test_jwt_token_refresh_on_expiry(self):
        """Test JWT token automatic refresh when expired."""
        if not _HAVE_JWT:
            pytest.skip("PyJWT not installed")
        # Create service with very short expiration for testing
        service = JWTCredentialService(
            secret="test-secret",
            expiration_minutes=1,  # 1 minute
            use_session_state=False
        )
        await service.initialize()
        
        user_id = "refresh-test-user"
        mock_context = MockCallbackContext(user_id=user_id)
        
        # Create and save initial credential
        auth_config = service.create_auth_config(user_id)
        auth_config.exchanged_auth_credential = auth_config.raw_auth_credential
        await service.save_credential(auth_config, mock_context)
        
        original_token = auth_config.raw_auth_credential.http.credentials.token
        
        # Simulate token expiry by creating an expired token manually
        import jwt
        from datetime import datetime, timedelta, timezone
        
        expired_payload = {
            "sub": user_id,
            "exp": (datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()
        }
        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
        
        # Update stored credential with expired token
        auth_config.raw_auth_credential.http.credentials.token = expired_token
        auth_config.exchanged_auth_credential = auth_config.raw_auth_credential
        await service.save_credential(auth_config, mock_context)
        
        # Load credential - should trigger refresh
        loaded_cred = await service.load_credential(auth_config, mock_context)
        assert loaded_cred is not None
        
        refreshed_token = loaded_cred.http.credentials.token
        assert refreshed_token != expired_token  # Should be a new token
        assert not service.is_token_expired(refreshed_token)  # Should not be expired

    async def test_http_basic_auth_workflow(self):
        """Test HTTP Basic Auth complete workflow."""
        service = HTTPBasicAuthCredentialService(
            username="test-api-user",
            password="test-api-password",
            realm="Test API",
            use_session_state=False
        )
        
        await service.initialize()
        
        # Create auth config
        auth_config = service.create_auth_config()
        assert auth_config.raw_auth_credential.http.scheme == "basic"
        assert auth_config.raw_auth_credential.http.credentials.username == "test-api-user"
        assert auth_config.raw_auth_credential.http.credentials.password == "test-api-password"
        
        # Test auth header generation
        auth_header = service.get_auth_header()
        assert auth_header.startswith("Basic ")
        
        # Verify encoding/decoding
        decoded_username, decoded_password = service.decode_basic_auth(auth_header)
        assert decoded_username == "test-api-user"
        assert decoded_password == "test-api-password"
        
        # Test credential validation
        assert service.validate_credentials("test-api-user", "test-api-password") is True
        assert service.validate_credentials("wrong-user", "test-api-password") is False
        
        # Test storage workflow
        mock_context = MockCallbackContext()
        
        # Set exchanged_auth_credential for saving
        auth_config.exchanged_auth_credential = auth_config.raw_auth_credential
        await service.save_credential(auth_config, mock_context)
        loaded_cred = await service.load_credential(auth_config, mock_context)
        
        assert loaded_cred is not None
        assert loaded_cred.http.credentials.username == "test-api-user"
        assert loaded_cred.http.credentials.password == "test-api-password"

    async def test_credential_isolation_by_user(self):
        """Test that credentials are properly isolated by user and app."""
        service = HTTPBasicAuthCredentialService(
            username="shared-service-user",
            password="shared-service-password",
            use_session_state=False
        )
        await service.initialize()
        
        auth_config = service.create_auth_config()
        
        # Create contexts for different users
        context_user1 = MockCallbackContext(app_name="test_app", user_id="user1")
        context_user2 = MockCallbackContext(app_name="test_app", user_id="user2")
        context_different_app = MockCallbackContext(app_name="other_app", user_id="user1")
        
        # Save credential for user1
        auth_config.exchanged_auth_credential = auth_config.raw_auth_credential
        await service.save_credential(auth_config, context_user1)
        
        # User1 can load their credential
        loaded_user1 = await service.load_credential(auth_config, context_user1)
        assert loaded_user1 is not None
        
        # User2 cannot load user1's credential (different user)
        loaded_user2 = await service.load_credential(auth_config, context_user2)
        assert loaded_user2 is None
        
        # Different app cannot load credential (different app)
        loaded_different_app = await service.load_credential(auth_config, context_different_app)
        assert loaded_different_app is None

    async def test_multiple_credential_services_coexistence(self):
        """Test that multiple credential services can coexist."""
        # Initialize multiple services
        google_service = GoogleOAuth2CredentialService(
            client_id="google-id", 
            client_secret="google-secret",
            use_session_state=False
        )
        
        if _HAVE_JWT:
            jwt_service = JWTCredentialService(
                secret="jwt-secret",
                use_session_state=False
            )
        
        basic_auth_service = HTTPBasicAuthCredentialService(
            username="basic-user",
            password="basic-pass",
            use_session_state=False
        )
        
        await google_service.initialize()
        if _HAVE_JWT:
            await jwt_service.initialize()
        await basic_auth_service.initialize()
        
        # Create different auth configs
        google_config = google_service.create_auth_config()
        jwt_config = jwt_service.create_auth_config("test-user") if _HAVE_JWT else None
        basic_config = basic_auth_service.create_auth_config()
        
        mock_context = MockCallbackContext()
        
        # Save all credentials
        google_config.exchanged_auth_credential = google_config.raw_auth_credential
        if _HAVE_JWT:
            jwt_config.exchanged_auth_credential = jwt_config.raw_auth_credential
        basic_config.exchanged_auth_credential = basic_config.raw_auth_credential
        
        await google_service.save_credential(google_config, mock_context)
        if _HAVE_JWT:
            await jwt_service.save_credential(jwt_config, mock_context)
        await basic_auth_service.save_credential(basic_config, mock_context)
        
        # Load all credentials - they should not interfere with each other
        loaded_google = await google_service.load_credential(google_config, mock_context)
        loaded_jwt = await jwt_service.load_credential(jwt_config, mock_context) if _HAVE_JWT else None
        loaded_basic = await basic_auth_service.load_credential(basic_config, mock_context)
        
        assert loaded_google is not None
        if _HAVE_JWT:
            assert loaded_jwt is not None
        assert loaded_basic is not None
        
        # Verify each credential has correct type and data
        assert loaded_google.auth_type.value == "oauth2"
        if _HAVE_JWT:
            assert loaded_jwt.auth_type.value == "http"
            assert loaded_jwt.http.scheme == "bearer"
        assert loaded_basic.auth_type.value == "http"
        assert loaded_basic.http.scheme == "basic"

    async def test_cleanup_lifecycle(self):
        """Test proper cleanup of credential services."""
        services = [
            GoogleOAuth2CredentialService("id", "secret", use_session_state=False),
            HTTPBasicAuthCredentialService("user", "pass", use_session_state=False),
        ]
        if _HAVE_JWT:
            services.insert(1, JWTCredentialService("secret", use_session_state=False))
        
        # Initialize all services
        for service in services:
            await service.initialize()
            assert service._initialized is True
        
        # Cleanup all services
        for service in services:
            await service.cleanup()
            assert service._initialized is False
        
        # Services should require re-initialization
        for service in services:
            with pytest.raises(RuntimeError, match="must be initialized"):
                service._check_initialized()
