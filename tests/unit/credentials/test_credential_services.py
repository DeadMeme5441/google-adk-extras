"""Unit tests for credential services."""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
try:
    import jwt
except Exception:
    jwt = None

from google_adk_extras.credentials import (
    BaseCustomCredentialService,
    GoogleOAuth2CredentialService,
    GitHubOAuth2CredentialService,
    MicrosoftOAuth2CredentialService,
    XOAuth2CredentialService,
    HTTPBasicAuthCredentialService,
    HTTPBasicAuthWithCredentialsService,
)
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes
from google.adk.auth.credential_service.base_credential_service import CallbackContext


class TestBaseCustomCredentialService:
    """Test cases for BaseCustomCredentialService."""

    class ConcreteCredentialService(BaseCustomCredentialService):
        """Concrete implementation for testing."""
        
        async def _initialize_impl(self):
            pass
            
        async def load_credential(self, auth_config, callback_context):
            return None
            
        async def save_credential(self, auth_config, callback_context):
            pass

    @pytest.mark.asyncio
    async def test_initialization_lifecycle(self):
        """Test initialization and cleanup lifecycle."""
        service = self.ConcreteCredentialService()
        
        # Initially not initialized
        assert not service._initialized
        
        # Check initialization required
        with pytest.raises(RuntimeError, match="must be initialized"):
            service._check_initialized()
        
        # Initialize
        await service.initialize()
        assert service._initialized
        
        # Can call multiple times without error
        await service.initialize()
        assert service._initialized
        
        # Cleanup
        await service.cleanup()
        assert not service._initialized


class TestGoogleOAuth2CredentialService:
    """Test cases for GoogleOAuth2CredentialService."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        service = GoogleOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret"
        )
        
        assert service.client_id == "test-client-id"
        assert service.client_secret == "test-client-secret"
        assert service.scopes == ["openid", "email", "profile"]
        assert service.use_session_state is True

    def test_init_with_custom_scopes(self):
        """Test initialization with custom scopes."""
        scopes = ["calendar", "gmail.readonly"]
        service = GoogleOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=scopes
        )
        
        assert service.scopes == scopes
        expected_resolved = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.readonly"
        ]
        assert service._resolved_scopes == expected_resolved

    @pytest.mark.asyncio
    async def test_initialization_validation(self):
        """Test initialization validation."""
        # Missing client_id
        service = GoogleOAuth2CredentialService(
            client_id="",
            client_secret="test-secret"
        )
        with pytest.raises(ValueError, match="client_id is required"):
            await service.initialize()

        # Missing client_secret
        service = GoogleOAuth2CredentialService(
            client_id="test-id",
            client_secret=""
        )
        with pytest.raises(ValueError, match="client_secret is required"):
            await service.initialize()

    @pytest.mark.asyncio
    async def test_create_auth_config(self):
        """Test auth config creation."""
        service = GoogleOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=["openid", "calendar"]
        )
        await service.initialize()
        
        auth_config = service.create_auth_config()
        
        assert auth_config.auth_scheme is not None
        assert auth_config.raw_auth_credential is not None
        assert auth_config.raw_auth_credential.auth_type == AuthCredentialTypes.OAUTH2
        assert auth_config.raw_auth_credential.oauth2.client_id == "test-client-id"

    def test_get_supported_scopes(self):
        """Test getting supported scopes."""
        service = GoogleOAuth2CredentialService(
            client_id="test-id",
            client_secret="test-secret"
        )
        
        scopes = service.get_supported_scopes()
        assert isinstance(scopes, dict)
        assert "openid" in scopes
        assert "calendar" in scopes


class TestGitHubOAuth2CredentialService:
    """Test cases for GitHubOAuth2CredentialService."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        service = GitHubOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret"
        )
        
        assert service.client_id == "test-client-id"
        assert service.client_secret == "test-client-secret"
        assert service.scopes == ["user", "repo"]

    @pytest.mark.asyncio
    async def test_initialization_with_unknown_scopes(self):
        """Test initialization with unknown scopes logs warning."""
        service = GitHubOAuth2CredentialService(
            client_id="test-id",
            client_secret="test-secret",
            scopes=["user", "unknown_scope"]
        )
        
        with patch('google_adk_extras.credentials.github_oauth2_credential_service.logger') as mock_logger:
            await service.initialize()
            mock_logger.warning.assert_called_once()
            assert "unknown_scope" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_create_auth_config(self):
        """Test auth config creation."""
        service = GitHubOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=["user", "repo"]
        )
        await service.initialize()
        
        auth_config = service.create_auth_config()
        
        assert auth_config.auth_scheme is not None
        assert auth_config.raw_auth_credential is not None
        assert auth_config.raw_auth_credential.auth_type == AuthCredentialTypes.OAUTH2


class TestMicrosoftOAuth2CredentialService:
    """Test cases for MicrosoftOAuth2CredentialService."""

    def test_init_with_tenant(self):
        """Test initialization with tenant ID."""
        service = MicrosoftOAuth2CredentialService(
            tenant_id="common",
            client_id="test-client-id",
            client_secret="test-client-secret"
        )
        
        assert service.tenant_id == "common"
        assert service.client_id == "test-client-id"

    def test_url_generation(self):
        """Test auth and token URL generation."""
        service = MicrosoftOAuth2CredentialService(
            tenant_id="test-tenant",
            client_id="test-id",
            client_secret="test-secret"
        )
        
        auth_url = service._get_auth_url("test-tenant")
        token_url = service._get_token_url("test-tenant")
        
        assert "test-tenant" in auth_url
        assert "test-tenant" in token_url
        assert "oauth2/v2.0" in auth_url
        assert "oauth2/v2.0" in token_url

    @pytest.mark.asyncio
    async def test_initialization_validation(self):
        """Test initialization validation."""
        # Missing tenant_id
        service = MicrosoftOAuth2CredentialService(
            tenant_id="",
            client_id="test-id",
            client_secret="test-secret"
        )
        with pytest.raises(ValueError, match="tenant_id is required"):
            await service.initialize()


class TestXOAuth2CredentialService:
    """Test cases for XOAuth2CredentialService."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        service = XOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret"
        )
        
        assert service.scopes == ["tweet.read", "users.read", "offline.access"]

    @pytest.mark.asyncio
    async def test_create_auth_config(self):
        """Test auth config creation."""
        service = XOAuth2CredentialService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=["tweet.read", "tweet.write"]
        )
        await service.initialize()
        
        auth_config = service.create_auth_config()
        
        assert auth_config.auth_scheme is not None
        assert auth_config.raw_auth_credential is not None
        assert auth_config.raw_auth_credential.auth_type == AuthCredentialTypes.OAUTH2


class TestJWTCredentialService:
    """Test cases for JWTCredentialService."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
        service = JWTCredentialService(
            secret="test-secret"
        )
        
        assert service.secret == "test-secret"
        assert service.algorithm == "HS256"
        assert service.expiration_minutes == 60

    @pytest.mark.asyncio
    async def test_initialization_validation(self):
        """Test initialization validation."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
        # Missing secret
        service = JWTCredentialService(secret="")
        with pytest.raises(ValueError, match="JWT secret is required"):
            await service.initialize()

        # Invalid algorithm
        service = JWTCredentialService(
            secret="test-secret",
            algorithm="INVALID"
        )
        with pytest.raises(ValueError, match="Unsupported JWT algorithm"):
            await service.initialize()

        # Invalid expiration
        service = JWTCredentialService(
            secret="test-secret",
            expiration_minutes=-1
        )
        with pytest.raises(ValueError, match="expiration_minutes must be positive"):
            await service.initialize()

    @pytest.mark.asyncio
    async def test_jwt_token_generation(self):
        """Test JWT token generation and verification."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
        service = JWTCredentialService(
            secret="test-secret",
            issuer="test-issuer",
            audience="test-audience",
            expiration_minutes=5
        )
        await service.initialize()
        
        # Generate token
        user_id = "test-user"
        token = service.generate_jwt_token(user_id, {"role": "admin"})
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token
        payload = service.verify_jwt_token(token)
        assert payload["sub"] == user_id
        assert payload["iss"] == "test-issuer"
        assert payload["aud"] == "test-audience"
        assert payload["role"] == "admin"

    @pytest.mark.asyncio
    async def test_token_expiration(self):
        """Test JWT token expiration detection."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
        service = JWTCredentialService(
            secret="test-secret",
            expiration_minutes=1
        )
        await service.initialize()
        
        # Create expired token manually
        past_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        expired_payload = {
            "sub": "test-user",
            "exp": past_time.timestamp()
        }
        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
        
        # Check expiration
        assert service.is_token_expired(expired_token) is True

    @pytest.mark.asyncio
    async def test_create_auth_config(self):
        """Test auth config creation with JWT."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
        service = JWTCredentialService(secret="test-secret")
        await service.initialize()
        
        auth_config = service.create_auth_config("test-user")
        
        assert auth_config.auth_scheme is not None
        assert auth_config.raw_auth_credential is not None
        assert auth_config.raw_auth_credential.auth_type == AuthCredentialTypes.HTTP
        assert auth_config.raw_auth_credential.http.scheme == "bearer"

    def test_get_token_info(self):
        """Test getting token information."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService
        service = JWTCredentialService(secret="test-secret")
        
        # Create a test token
        payload = {
            "sub": "test-user",
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        info = service.get_token_info(token)
        assert "payload" in info
        assert "expired" in info
        assert info["payload"]["sub"] == "test-user"


class TestHTTPBasicAuthCredentialService:
    """Test cases for HTTPBasicAuthCredentialService."""

    def test_init(self):
        """Test initialization."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password",
            realm="Test Realm"
        )
        
        assert service.username == "test-user"
        assert service.password == "test-password"
        assert service.realm == "Test Realm"

    @pytest.mark.asyncio
    async def test_initialization_validation(self):
        """Test initialization validation."""
        # Missing username
        service = HTTPBasicAuthCredentialService(
            username="",
            password="test-password"
        )
        with pytest.raises(ValueError, match="Username is required"):
            await service.initialize()

        # Missing password
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password=""
        )
        with pytest.raises(ValueError, match="Password is required"):
            await service.initialize()

    def test_encode_decode_basic_auth(self):
        """Test Basic Auth encoding and decoding."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password"
        )
        
        # Test encoding
        encoded = service.encode_basic_auth("user", "pass")
        assert encoded.startswith("Basic ")
        
        # Test decoding
        username, password = service.decode_basic_auth(encoded)
        assert username == "user"
        assert password == "pass"

    def test_decode_invalid_header(self):
        """Test decoding invalid Basic Auth header."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password"
        )
        
        with pytest.raises(ValueError, match="Invalid Basic Auth header format"):
            service.decode_basic_auth("Bearer token123")

    @pytest.mark.asyncio
    async def test_create_auth_config(self):
        """Test auth config creation."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password"
        )
        await service.initialize()
        
        auth_config = service.create_auth_config()
        
        assert auth_config.auth_scheme is not None
        assert auth_config.raw_auth_credential is not None
        assert auth_config.raw_auth_credential.auth_type == AuthCredentialTypes.HTTP
        assert auth_config.raw_auth_credential.http.scheme == "basic"

    @pytest.mark.asyncio
    async def test_validate_credentials(self):
        """Test credential validation."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password"
        )
        await service.initialize()
        
        assert service.validate_credentials("test-user", "test-password") is True
        assert service.validate_credentials("wrong-user", "test-password") is False
        assert service.validate_credentials("test-user", "wrong-password") is False

    @pytest.mark.asyncio
    async def test_get_auth_header(self):
        """Test getting authorization header."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password"
        )
        await service.initialize()
        
        header = service.get_auth_header()
        assert header.startswith("Basic ")
        
        # Decode to verify
        username, password = service.decode_basic_auth(header)
        assert username == "test-user"
        assert password == "test-password"

    @pytest.mark.asyncio
    async def test_get_credential_info(self):
        """Test getting credential information."""
        service = HTTPBasicAuthCredentialService(
            username="test-user",
            password="test-password",
            realm="Test Realm"
        )
        await service.initialize()
        
        info = service.get_credential_info()
        assert info["username"] == "test-user"
        assert info["auth_type"] == "HTTP Basic Auth"
        assert info["password_set"] is True
        assert info["realm"] == "Test Realm"


class TestHTTPBasicAuthWithCredentialsService:
    """Test cases for HTTPBasicAuthWithCredentialsService."""

    def test_init_with_multiple_credentials(self):
        """Test initialization with multiple credentials."""
        credentials = {
            "admin": "admin-pass",
            "user1": "user1-pass",
            "user2": "user2-pass"
        }
        service = HTTPBasicAuthWithCredentialsService(
            credentials=credentials,
            default_username="admin"
        )
        
        assert service.credentials == credentials
        assert service.default_username == "admin"

    def test_init_with_auto_default(self):
        """Test initialization with automatic default username selection."""
        credentials = {"user1": "pass1"}
        service = HTTPBasicAuthWithCredentialsService(credentials=credentials)
        
        assert service.default_username == "user1"

    @pytest.mark.asyncio
    async def test_initialization_validation(self):
        """Test initialization validation."""
        # Empty credentials
        service = HTTPBasicAuthWithCredentialsService(credentials={})
        with pytest.raises(ValueError, match="At least one username/password pair"):
            await service.initialize()

        # Invalid default username
        service = HTTPBasicAuthWithCredentialsService(
            credentials={"user1": "pass1"},
            default_username="nonexistent"
        )
        with pytest.raises(ValueError, match="Default username .* not found"):
            await service.initialize()

    @pytest.mark.asyncio
    async def test_create_auth_config_default_user(self):
        """Test auth config creation with default user."""
        credentials = {"admin": "admin-pass", "user": "user-pass"}
        service = HTTPBasicAuthWithCredentialsService(
            credentials=credentials,
            default_username="admin"
        )
        await service.initialize()
        
        # Use default username
        auth_config = service.create_auth_config()
        assert auth_config.raw_auth_credential.http.credentials.username == "admin"

    @pytest.mark.asyncio
    async def test_create_auth_config_specific_user(self):
        """Test auth config creation with specific user."""
        credentials = {"admin": "admin-pass", "user": "user-pass"}
        service = HTTPBasicAuthWithCredentialsService(
            credentials=credentials,
            default_username="admin"
        )
        await service.initialize()
        
        # Use specific username
        auth_config = service.create_auth_config("user")
        assert auth_config.raw_auth_credential.http.credentials.username == "user"

    @pytest.mark.asyncio
    async def test_create_auth_config_invalid_user(self):
        """Test auth config creation with invalid user."""
        credentials = {"admin": "admin-pass"}
        service = HTTPBasicAuthWithCredentialsService(
            credentials=credentials,
            default_username="admin"
        )
        await service.initialize()
        
        with pytest.raises(ValueError, match="Username .* not found in credentials"):
            service.create_auth_config("nonexistent")

    def test_get_available_usernames(self):
        """Test getting available usernames."""
        credentials = {"admin": "admin-pass", "user1": "pass1", "user2": "pass2"}
        service = HTTPBasicAuthWithCredentialsService(credentials=credentials)
        
        usernames = service.get_available_usernames()
        assert set(usernames) == {"admin", "user1", "user2"}
