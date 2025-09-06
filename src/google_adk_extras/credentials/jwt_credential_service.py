"""JWT credential service implementation."""

from typing import Optional, Dict, Any
import logging
import jwt
from datetime import datetime, timedelta, timezone

from google.adk.auth.credential_service.session_state_credential_service import SessionStateCredentialService
from google.adk.auth.credential_service.base_credential_service import CallbackContext
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_credential import HttpAuth, HttpCredentials
from fastapi.openapi.models import HTTPBearer

from .base_custom_credential_service import BaseCustomCredentialService

logger = logging.getLogger(__name__)


class JWTCredentialService(BaseCustomCredentialService):
    """JWT credential service for handling JSON Web Token authentication.
    
    This service generates and manages JWT tokens for API authentication.
    It supports both short-lived and long-lived tokens with automatic refresh.
    
    Args:
        secret: The secret key used to sign JWT tokens.
        algorithm: The algorithm used for JWT signing. Default is 'HS256'.
        issuer: The issuer of the JWT token. Optional.
        audience: The intended audience of the JWT token. Optional.
        expiration_minutes: Token expiration time in minutes. Default is 60 minutes.
        custom_claims: Additional custom claims to include in the JWT payload.
        use_session_state: If True, stores credentials in session state. If False,
            uses in-memory storage. Default is True for persistence.
    
    Example:
        ```python
        credential_service = JWTCredentialService(
            secret="your-jwt-secret",
            algorithm="HS256",
            issuer="my-app",
            audience="api.example.com",
            expiration_minutes=120,
            custom_claims={"role": "admin", "permissions": ["read", "write"]}
        )
        await credential_service.initialize()
        
        # Use with Runner
        runner = Runner(
            agent=agent,
            session_service=session_service,
            credential_service=credential_service,
            app_name="my_app"
        )
        ```
    """

    SUPPORTED_ALGORITHMS = {
        'HS256', 'HS384', 'HS512',  # HMAC with SHA
        'RS256', 'RS384', 'RS512',  # RSA with SHA
        'ES256', 'ES384', 'ES512'   # ECDSA with SHA
    }

    def __init__(
        self,
        secret: str,
        algorithm: str = 'HS256',
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        expiration_minutes: int = 60,
        custom_claims: Optional[Dict[str, Any]] = None,
        use_session_state: bool = True
    ):
        """Initialize the JWT credential service.
        
        Args:
            secret: JWT signing secret.
            algorithm: JWT signing algorithm.
            issuer: JWT issuer.
            audience: JWT audience.
            expiration_minutes: Token expiration in minutes.
            custom_claims: Additional claims to include in JWT.
            use_session_state: Whether to use session state for credential storage.
        """
        super().__init__()
        self.secret = secret
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.expiration_minutes = expiration_minutes
        self.custom_claims = custom_claims or {}
        self.use_session_state = use_session_state
        
        # Underlying credential service for storage
        if use_session_state:
            self._storage_service = SessionStateCredentialService()
        else:
            from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
            self._storage_service = InMemoryCredentialService()

    async def _initialize_impl(self) -> None:
        """Initialize the JWT credential service.
        
        Validates the configuration parameters.
        
        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.secret:
            raise ValueError("JWT secret is required")
        
        if self.algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported JWT algorithm: {self.algorithm}. Supported: {self.SUPPORTED_ALGORITHMS}")
        
        if self.expiration_minutes <= 0:
            raise ValueError("JWT expiration_minutes must be positive")
            
        # Test JWT creation to validate secret and algorithm
        try:
            test_payload = {"test": "validation"}
            jwt.encode(test_payload, self.secret, algorithm=self.algorithm)
            logger.info(f"Initialized JWT credential service with algorithm {self.algorithm}")
        except Exception as e:
            raise ValueError(f"Invalid JWT configuration: {e}")

    def generate_jwt_token(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Generate a JWT token for the specified user.
        
        Args:
            user_id: The user ID to include in the JWT token.
            additional_claims: Additional claims to include in this specific token.
            
        Returns:
            str: The generated JWT token.
            
        Raises:
            RuntimeError: If the service is not initialized.
        """
        self._check_initialized()
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=self.expiration_minutes)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "iat": now,      # Issued at
            "exp": exp,      # Expiration
        }
        
        # Add optional standard claims
        if self.issuer:
            payload["iss"] = self.issuer
        if self.audience:
            payload["aud"] = self.audience
            
        # Add custom claims
        payload.update(self.custom_claims)
        if additional_claims:
            payload.update(additional_claims)
            
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        logger.debug(f"Generated JWT token for user {user_id} expiring at {exp}")
        
        return token

    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token.
        
        Args:
            token: The JWT token to verify.
            
        Returns:
            Dict[str, Any]: The decoded token payload.
            
        Raises:
            jwt.InvalidTokenError: If the token is invalid or expired.
            RuntimeError: If the service is not initialized.
        """
        self._check_initialized()
        
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
        }
        
        # Set audience verification if configured
        audience = self.audience if self.audience else None
        issuer = self.issuer if self.issuer else None
        
        payload = jwt.decode(
            token,
            self.secret,
            algorithms=[self.algorithm],
            audience=audience,
            issuer=issuer,
            options=options
        )
        
        return payload

    def is_token_expired(self, token: str) -> bool:
        """Check if a JWT token is expired without raising an exception.
        
        Args:
            token: The JWT token to check.
            
        Returns:
            bool: True if the token is expired, False otherwise.
        """
        try:
            self.verify_jwt_token(token)
            return False
        except jwt.ExpiredSignatureError:
            return True
        except jwt.InvalidTokenError:
            # Other validation errors also count as "expired" for refresh purposes
            return True

    def create_auth_config(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> AuthConfig:
        """Create an AuthConfig with a generated JWT token.
        
        Args:
            user_id: The user ID for the JWT token.
            additional_claims: Additional claims for this specific token.
            
        Returns:
            AuthConfig: Configured auth config with JWT Bearer token.
        """
        self._check_initialized()
        
        # Generate JWT token
        token = self.generate_jwt_token(user_id, additional_claims)
        
        # Create HTTP Bearer auth scheme
        auth_scheme = HTTPBearer()
        
        # Create HTTP Bearer credential
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.HTTP,
            http=HttpAuth(
                scheme="bearer",
                credentials=HttpCredentials(token=token)
            )
        )
        
        return AuthConfig(
            auth_scheme=auth_scheme,
            raw_auth_credential=auth_credential
        )

    async def load_credential(
        self,
        auth_config: AuthConfig,
        callback_context: CallbackContext,
    ) -> Optional[AuthCredential]:
        """Load JWT credential from storage and refresh if expired.
        
        Args:
            auth_config: The auth config containing credential key information.
            callback_context: The current callback context.
            
        Returns:
            Optional[AuthCredential]: The stored credential or refreshed credential.
        """
        self._check_initialized()
        
        # Load existing credential
        credential = await self._storage_service.load_credential(auth_config, callback_context)
        
        if not credential or not credential.http or not credential.http.credentials:
            return None
            
        # Check if token needs refresh
        token = credential.http.credentials.token
        if not token or self.is_token_expired(token):
            logger.info(f"JWT token expired for user {callback_context._invocation_context.user_id}, generating new token")
            
            # Generate new token
            user_id = callback_context._invocation_context.user_id
            new_token = self.generate_jwt_token(user_id)
            
            # Update credential with new token
            credential.http.credentials.token = new_token
            
            # Save refreshed credential
            updated_auth_config = AuthConfig(
                auth_scheme=auth_config.auth_scheme,
                raw_auth_credential=credential,
                exchanged_auth_credential=credential
            )
            await self._storage_service.save_credential(updated_auth_config, callback_context)
            
        return credential

    async def save_credential(
        self,
        auth_config: AuthConfig,
        callback_context: CallbackContext,
    ) -> None:
        """Save JWT credential to storage.
        
        Args:
            auth_config: The auth config containing the credential to save.
            callback_context: The current callback context.
        """
        self._check_initialized()
        await self._storage_service.save_credential(auth_config, callback_context)
        
        logger.info(f"Saved JWT credential for user {callback_context._invocation_context.user_id}")

    def get_token_info(self, token: str) -> Dict[str, Any]:
        """Get information about a JWT token without full verification.
        
        Args:
            token: The JWT token to inspect.
            
        Returns:
            Dict[str, Any]: Token information including claims and expiration.
        """
        try:
            # Decode without verification to get token info
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Check expiration without requiring initialization
            expired = True
            if self._initialized:
                expired = self.is_token_expired(token)
            elif "exp" in payload:
                # Simple expiration check without initialization
                exp_timestamp = payload["exp"]
                expired = datetime.now(timezone.utc).timestamp() > exp_timestamp
            
            info = {
                "payload": payload,
                "expired": expired,
            }
            
            if "exp" in payload:
                exp_timestamp = payload["exp"]
                exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
                info["expires_at"] = exp_datetime.isoformat()
                
            return info
        except Exception as e:
            return {"error": str(e), "expired": True}