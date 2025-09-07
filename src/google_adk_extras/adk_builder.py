"""AdkBuilder - Enhanced builder for Google ADK with credential service support.

This module provides the AdkBuilder class that extends Google ADK's FastAPI integration
with support for custom credential services and enhanced configuration options.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union, Callable
from starlette.types import Lifespan

from fastapi import FastAPI
from google.adk.runners import Runner
from google.adk.agents.base_agent import BaseAgent
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.artifacts.base_artifact_service import BaseArtifactService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
# GCS removed - vendor specific
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.auth.credential_service.base_credential_service import BaseCredentialService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader
from google.adk.cli.adk_web_server import AdkWebServer

from .custom_agent_loader import CustomAgentLoader
from .credentials.base_custom_credential_service import BaseCustomCredentialService

logger = logging.getLogger(__name__)


class AdkBuilder:
    """Builder for creating enhanced Google ADK applications with custom credential services.
    
    This builder extends Google ADK's capabilities by adding support for custom credential
    services while maintaining full compatibility with all ADK features including web UI,
    hot reloading, A2A protocol, and cloud deployment.
    
    Example:
        ```python
        from google_adk_extras import AdkBuilder
        from google_adk_extras.credentials import GoogleOAuth2CredentialService
        
        # Build FastAPI app with Google OAuth2 credentials
        app = (AdkBuilder()
               .with_agents_dir("./agents")
               .with_session_service("sqlite:///sessions.db")
               .with_credential_service(GoogleOAuth2CredentialService(
                   client_id="your-client-id",
                   client_secret="your-secret",
                   scopes=["calendar", "gmail.readonly"]
               ))
               .with_web_ui()
               .build_fastapi_app())
        
        # Or build a Runner directly  
        runner = (AdkBuilder()
                  .with_agents_dir("./agents")
                  .with_credential_service_uri("oauth2-google://client-id:secret@scopes=calendar,gmail.readonly")
                  .build_runner("my_agent"))
        ```
    """
    
    def __init__(self):
        """Initialize the AdkBuilder with default configuration."""
        # Core configuration
        self._agents_dir: Optional[str] = None
        self._app_name: Optional[str] = None
        
        # Service URIs (following ADK patterns)
        self._session_service_uri: Optional[str] = None
        self._artifact_service_uri: Optional[str] = None
        self._memory_service_uri: Optional[str] = None
        self._credential_service_uri: Optional[str] = None
        self._eval_storage_uri: Optional[str] = None
        
        # Service instances (alternative to URIs)
        self._session_service: Optional[BaseSessionService] = None
        self._artifact_service: Optional[BaseArtifactService] = None
        self._memory_service: Optional[BaseMemoryService] = None
        self._credential_service: Optional[BaseCredentialService] = None
        
        # Agent loading configuration
        self._agent_loader: Optional[BaseAgentLoader] = None
        self._registered_agents: Dict[str, BaseAgent] = {}
        
        # Database configuration
        self._session_db_kwargs: Optional[Mapping[str, Any]] = None
        
        # Web/FastAPI configuration
        self._allow_origins: Optional[List[str]] = None
        self._web_ui: bool = False
        self._a2a: bool = False
        # Programmatic A2A exposure (for registered/programmatic agents)
        self._a2a_expose_programmatic: bool = False
        self._a2a_programmatic_mount_base: str = "/a2a"
        self._a2a_card_factory: Optional[Callable[[str, BaseAgent], Dict[str, Any]]] = None
        self._host: str = "127.0.0.1"
        self._port: int = 8000
        self._trace_to_cloud: bool = False
        self._reload_agents: bool = False
        self._lifespan: Optional[Lifespan[FastAPI]] = None

        # Staging list for remote A2A agents to register (if import is deferred)
        self._pending_remote_a2a: List[Dict[str, str]] = []

    # Core configuration methods
    def with_agents_dir(self, agents_dir: str) -> "AdkBuilder":
        """Set the directory containing agent definitions.
        
        Args:
            agents_dir: Path to directory containing agent subdirectories.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._agents_dir = agents_dir
        return self

    def with_app_name(self, app_name: str) -> "AdkBuilder":
        """Set the application name.
        
        Args:
            app_name: Name of the application.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._app_name = app_name
        return self

    # Service URI methods (following ADK patterns)
    def with_session_service(self, uri: str, **db_kwargs) -> "AdkBuilder":
        """Configure session service using URI.
        
        Supported URIs:
        - "sqlite:///./sessions.db" - SQLite database
        - "postgresql://user:pass@host/db" - PostgreSQL database  
        - "yaml://path/to/sessions.yaml" - YAML file session storage
        - "redis://localhost:6379" - Redis session storage
        - "mongodb://localhost:27017/sessions" - MongoDB session storage
        
        Args:
            uri: Session service URI.
            **db_kwargs: Additional database configuration options.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._session_service_uri = uri
        if db_kwargs:
            self._session_db_kwargs = db_kwargs
        return self

    def with_artifact_service(self, uri: str) -> "AdkBuilder":
        """Configure artifact service using URI.
        
        Supported URIs:
        - "gs://bucket-name" - Google Cloud Storage
        
        Args:
            uri: Artifact service URI.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._artifact_service_uri = uri
        return self

    def with_memory_service(self, uri: str) -> "AdkBuilder":
        """Configure memory service using URI.
        
        Supported URIs:
        - "yaml://path/to/memory.yaml" - YAML file memory storage
        - "redis://localhost:6379" - Redis memory storage
        - "sqlite:///./memory.db" - SQLite database
        - "postgresql://user:pass@host/db" - PostgreSQL database
        - "mongodb://localhost:27017/memory" - MongoDB memory storage
        
        Args:
            uri: Memory service URI.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._memory_service_uri = uri
        return self

    def with_credential_service_uri(self, uri: str) -> "AdkBuilder":
        """Configure credential service using URI.
        
        Supported URIs:
        - "oauth2-google://client-id:secret@scopes=scope1,scope2"
        - "oauth2-github://client-id:secret@scopes=user,repo"  
        - "oauth2-microsoft://tenant-id/client-id:secret@scopes=User.Read"
        - "oauth2-x://client-id:secret@scopes=tweet.read,users.read"
        - "jwt://secret@algorithm=HS256&issuer=my-app&audience=api.example.com&expiration_minutes=60"
        - "basic-auth://username:password@realm=My API"
        
        Args:
            uri: Credential service URI.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._credential_service_uri = uri
        return self

    def with_eval_storage(self, uri: str) -> "AdkBuilder":
        """Configure evaluation storage using URI.
        
        Args:
            uri: Evaluation storage URI.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._eval_storage_uri = uri
        return self

    # Service instance methods (alternative to URIs)
    def with_session_service_instance(self, service: BaseSessionService) -> "AdkBuilder":
        """Configure session service using service instance.
        
        Args:
            service: Session service instance.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._session_service = service
        return self

    def with_artifact_service_instance(self, service: BaseArtifactService) -> "AdkBuilder":
        """Configure artifact service using service instance.
        
        Args:
            service: Artifact service instance.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._artifact_service = service
        return self

    def with_memory_service_instance(self, service: BaseMemoryService) -> "AdkBuilder":
        """Configure memory service using service instance.
        
        Args:
            service: Memory service instance.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._memory_service = service
        return self

    def with_credential_service(self, service: BaseCredentialService) -> "AdkBuilder":
        """Configure credential service using service instance.
        
        Args:
            service: Credential service instance (our custom services or ADK services).
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._credential_service = service
        return self

    # Web/FastAPI configuration methods
    def with_web_ui(self, enabled: bool = True) -> "AdkBuilder":
        """Enable or disable the web development UI.
        
        Args:
            enabled: Whether to enable web UI. Defaults to True.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._web_ui = enabled
        return self

    def with_cors(self, allow_origins: List[str]) -> "AdkBuilder":
        """Configure CORS allowed origins.
        
        Args:
            allow_origins: List of allowed origins for CORS.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._allow_origins = allow_origins
        return self

    def with_a2a_protocol(self, enabled: bool = True) -> "AdkBuilder":
        """Enable or disable Agent-to-Agent protocol support.
        
        Args:
            enabled: Whether to enable A2A protocol. Defaults to True.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._a2a = enabled
        return self

    def enable_a2a_for_registered_agents(
        self,
        *,
        enabled: bool = True,
        mount_base: str = "/a2a",
        card_factory: Optional[Callable[[str, BaseAgent], Dict[str, Any]]] = None,
    ) -> "AdkBuilder":
        """Expose programmatically registered agents over A2A.

        This enables A2A for agents added via with_agent_instance()/with_agents()
        without requiring an `agents_dir`. Optionally provide a `card_factory`
        to generate Agent Card dictionaries for each agent.

        Args:
            enabled: Toggle exposure.
            mount_base: Base path to mount A2A routes, default "/a2a".
            card_factory: Optional callable (name, agent) -> dict for AgentCard.

        Returns:
            AdkBuilder: Self for chaining.
        """
        self._a2a_expose_programmatic = enabled
        self._a2a_programmatic_mount_base = mount_base
        self._a2a_card_factory = card_factory
        return self

    def with_remote_a2a_agent(
        self, name: str, agent_card_url: str, description: Optional[str] = None
    ) -> "AdkBuilder":
        """Register a remote A2A agent (client proxy) by agent card URL.

        Attempts to instantiate ADK's RemoteA2aAgent and register it by name.
        Requires ADK installed with A2A extras: `pip install google-adk[a2a]`.

        Args:
            name: Logical name to register.
            agent_card_url: Full URL to the remote agent card (well-known path).
            description: Optional description.

        Returns:
            AdkBuilder: Self for chaining.
        """
        # Try multiple likely import paths to be robust across ADK versions
        RemoteA2aAgent = None  # type: ignore
        import_error: Optional[Exception] = None
        for path in (
            "google.adk.a2a.remote_a2a_agent",
            "google.adk.a2a.remote_agent",
            "google.adk.a2a.client.remote_a2a_agent",
        ):
            try:
                module = __import__(path, fromlist=["RemoteA2aAgent"])  # type: ignore
                RemoteA2aAgent = getattr(module, "RemoteA2aAgent")  # type: ignore
                break
            except Exception as e:  # ImportError or AttributeError
                import_error = e
                continue

        if RemoteA2aAgent is None:
            raise ImportError(
                "Could not import RemoteA2aAgent from ADK. Ensure A2A extras are installed: "
                "pip install google-adk[a2a]. Last error: %r" % (import_error,)
            )

        # Instantiate and register
        remote = RemoteA2aAgent(
            name=name,
            description=description or name,
            agent_card=agent_card_url,
        )
        # Do not enforce BaseAgent type here; RemoteA2aAgent should be compatible
        self._registered_agents[name] = remote
        logger.info("Registered remote A2A agent: %s", name)
        return self

    def with_host_port(self, host: str = "127.0.0.1", port: int = 8000) -> "AdkBuilder":
        """Configure host and port for the server.
        
        Args:
            host: Host address. Defaults to "127.0.0.1".
            port: Port number. Defaults to 8000.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._host = host
        self._port = port
        return self

    def with_cloud_tracing(self, enabled: bool = True) -> "AdkBuilder":
        """Enable or disable cloud tracing.
        
        Args:
            enabled: Whether to enable cloud tracing. Defaults to True.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._trace_to_cloud = enabled
        return self

    def with_agent_reload(self, enabled: bool = True) -> "AdkBuilder":
        """Enable or disable hot reloading of agents during development.
        
        Args:
            enabled: Whether to enable agent hot reloading. Defaults to True.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._reload_agents = enabled
        return self

    def with_lifespan(self, lifespan: Lifespan[FastAPI]) -> "AdkBuilder":
        """Configure FastAPI lifespan events.
        
        Args:
            lifespan: FastAPI lifespan callable.
            
        Returns:
            AdkBuilder: Self for method chaining.
        """
        self._lifespan = lifespan
        return self

    # Agent configuration methods
    def with_agent_instance(self, name: str, agent: BaseAgent) -> "AdkBuilder":
        """Register an agent instance by name for programmatic agent control.
        
        This allows you to define agents purely in code without requiring
        directory structures or file-based definitions.
        
        Args:
            name: Agent name for discovery and loading.
            agent: BaseAgent instance to register.
            
        Returns:
            AdkBuilder: Self for method chaining.
            
        Example:
            ```python
            from google.adk.agents import Agent
            
            my_agent = Agent(
                name="dynamic_agent",
                model="gemini-2.0-flash",
                instructions="You are a helpful assistant."
            )
            
            app = (AdkBuilder()
                   .with_agent_instance("my_agent", my_agent)
                   .build_fastapi_app())
            ```
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")
            
        if not isinstance(agent, BaseAgent):
            raise ValueError(f"Agent must be BaseAgent instance, got {type(agent)}")
        
        self._registered_agents[name] = agent
        logger.info("Registered agent instance: %s", name)
        return self
    
    def with_agents(self, agents_dict: Dict[str, BaseAgent]) -> "AdkBuilder":
        """Register multiple agent instances at once.
        
        Args:
            agents_dict: Dictionary mapping agent names to BaseAgent instances.
            
        Returns:
            AdkBuilder: Self for method chaining.
            
        Example:
            ```python
            agents = {
                "agent1": Agent(...),
                "agent2": Agent(...),
            }
            
            app = (AdkBuilder()
                   .with_agents(agents)
                   .build_fastapi_app())
            ```
        """
        if not isinstance(agents_dict, dict):
            raise ValueError("Agents must be a dictionary mapping names to BaseAgent instances")
        
        for name, agent in agents_dict.items():
            self.with_agent_instance(name, agent)
        return self
    
    def with_agent_loader(self, loader: BaseAgentLoader) -> "AdkBuilder":
        """Use a custom agent loader instead of directory-based loading.
        
        This provides full control over agent discovery and loading logic.
        The custom loader will be used instead of creating a default AgentLoader.
        
        Args:
            loader: BaseAgentLoader instance to use for agent loading.
            
        Returns:
            AdkBuilder: Self for method chaining.
            
        Example:
            ```python
            custom_loader = CustomAgentLoader()
            custom_loader.register_agent("agent1", my_agent)
            
            app = (AdkBuilder()
                   .with_agent_loader(custom_loader)
                   .build_fastapi_app())
            ```
        """
        if not isinstance(loader, BaseAgentLoader):
            raise ValueError(f"Agent loader must be BaseAgentLoader instance, got {type(loader)}")
        
        self._agent_loader = loader
        logger.info("Set custom agent loader: %s", type(loader).__name__)
        return self

    # Service creation methods
    def _create_session_service(self) -> BaseSessionService:
        """Create session service from configuration."""
        if self._session_service is not None:
            return self._session_service

        if self._session_service_uri:
            db_kwargs = self._session_db_kwargs or {}
            
            if self._session_service_uri.startswith("yaml://"):
                from .sessions.yaml_file_session_service import YamlFileSessionService
                base_directory = self._session_service_uri.split("://")[1]
                return YamlFileSessionService(base_directory=base_directory)
            elif self._session_service_uri.startswith("redis://"):
                from .sessions.redis_session_service import RedisSessionService
                return RedisSessionService(connection_string=self._session_service_uri)
            elif self._session_service_uri.startswith("mongodb://"):
                from .sessions.mongo_session_service import MongoSessionService
                return MongoSessionService(connection_string=self._session_service_uri)
            elif self._session_service_uri.startswith(("sqlite://", "postgresql://", "mysql://")):
                from .sessions.sql_session_service import SQLSessionService
                return SQLSessionService(database_url=self._session_service_uri)
            else:
                raise ValueError(f"Unsupported session service URI format: {self._session_service_uri}")
        
        return InMemorySessionService()

    def _create_artifact_service(self) -> BaseArtifactService:
        """Create artifact service from configuration."""
        if self._artifact_service is not None:
            return self._artifact_service

        if self._artifact_service_uri:
            if self._artifact_service_uri.startswith("local://"):
                from .artifacts.local_folder_artifact_service import LocalFolderArtifactService  
                base_directory = self._artifact_service_uri.split("://")[1]
                return LocalFolderArtifactService(base_directory=base_directory)
            elif self._artifact_service_uri.startswith("s3://"):
                from .artifacts.s3_artifact_service import S3ArtifactService
                bucket_name = self._artifact_service_uri.split("://")[1]
                return S3ArtifactService(bucket_name=bucket_name)
            elif self._artifact_service_uri.startswith(("sqlite://", "postgresql://", "mysql://")):
                from .artifacts.sql_artifact_service import SQLArtifactService
                return SQLArtifactService(database_url=self._artifact_service_uri)
            elif self._artifact_service_uri.startswith("mongodb://"):
                from .artifacts.mongo_artifact_service import MongoArtifactService
                return MongoArtifactService(connection_string=self._artifact_service_uri)
            else:
                raise ValueError(f"Unsupported artifact service URI: {self._artifact_service_uri}")
        
        return InMemoryArtifactService()

    def _create_memory_service(self) -> BaseMemoryService:
        """Create memory service from configuration."""
        if self._memory_service is not None:
            return self._memory_service

        if self._memory_service_uri:
            if self._memory_service_uri.startswith("yaml://"):
                from .memory.yaml_file_memory_service import YamlFileMemoryService
                base_directory = self._memory_service_uri.split("://")[1]
                return YamlFileMemoryService(base_directory=base_directory)
            elif self._memory_service_uri.startswith("redis://"):
                from .memory.redis_memory_service import RedisMemoryService
                return RedisMemoryService(connection_string=self._memory_service_uri)
            elif self._memory_service_uri.startswith(("sqlite://", "postgresql://", "mysql://")):
                from .memory.sql_memory_service import SQLMemoryService
                return SQLMemoryService(database_url=self._memory_service_uri)
            elif self._memory_service_uri.startswith("mongodb://"):
                from .memory.mongo_memory_service import MongoMemoryService
                return MongoMemoryService(connection_string=self._memory_service_uri)
            else:
                raise ValueError(f"Unsupported memory service URI: {self._memory_service_uri}")
        
        return InMemoryMemoryService()

    def _create_credential_service(self) -> Optional[BaseCredentialService]:
        """Create credential service from configuration (optional)."""
        if self._credential_service is not None:
            return self._credential_service

        if self._credential_service_uri:
            return self._parse_credential_service_uri(self._credential_service_uri)
        
        # No credential service configured; allow server to default
        return None
    
    def _create_agent_loader(self) -> BaseAgentLoader:
        """Create agent loader from configuration.
        
        Returns:
            BaseAgentLoader: Configured agent loader instance.
            
        Raises:
            ValueError: If no agent configuration is provided.
        """
        # If custom loader is provided, use it directly
        if self._agent_loader is not None:
            # If we also have registered agents, we need to register them
            if self._registered_agents:
                if isinstance(self._agent_loader, CustomAgentLoader):
                    # Register agents into the existing CustomAgentLoader
                    for name, agent in self._registered_agents.items():
                        self._agent_loader.register_agent(name, agent)
                    logger.info("Registered %d agents into existing CustomAgentLoader", 
                              len(self._registered_agents))
                else:
                    logger.warning(
                        "Custom agent loader is not CustomAgentLoader, but registered agents exist. "
                        "Registered agents will be ignored. Consider using CustomAgentLoader."
                    )
            return self._agent_loader
        
        # If we have registered agents, create CustomAgentLoader
        if self._registered_agents:
            # Create CustomAgentLoader (no fallback support)
            if self._agents_dir:
                raise ValueError("Cannot use agents_dir with registered agents - use either directory-based OR instance-based loading, not both")
            
            logger.info("Creating CustomAgentLoader with registered agents")
            custom_loader = CustomAgentLoader()
            
            # Register all agents
            for name, agent in self._registered_agents.items():
                custom_loader.register_agent(name, agent)
            
            logger.info("Registered %d agents into CustomAgentLoader", len(self._registered_agents))
            return custom_loader
        
        # If we only have agents_dir, create default AgentLoader
        if self._agents_dir:
            logger.info("Creating default AgentLoader for directory: %s", self._agents_dir)
            return AgentLoader(self._agents_dir)
        
        # No agent configuration provided
        raise ValueError(
            "No agent configuration provided. Use with_agents_dir(), with_agent_instance(), "
            "or with_agent_loader() to configure agents."
        )

    def _parse_credential_service_uri(self, uri: str) -> BaseCredentialService:
        """Parse credential service URI and create appropriate service.
        
        Args:
            uri: Credential service URI.
            
        Returns:
            BaseCredentialService: Configured credential service.
            
        Raises:
            ValueError: If URI format is invalid or unsupported.
        """
        try:
            if uri.startswith("oauth2-google://"):
                return self._parse_google_oauth2_uri(uri)
            elif uri.startswith("oauth2-github://"):
                return self._parse_github_oauth2_uri(uri)
            elif uri.startswith("oauth2-microsoft://"):
                return self._parse_microsoft_oauth2_uri(uri)
            elif uri.startswith("oauth2-x://"):
                return self._parse_x_oauth2_uri(uri)
            elif uri.startswith("jwt://"):
                return self._parse_jwt_uri(uri)
            elif uri.startswith("basic-auth://"):
                return self._parse_basic_auth_uri(uri)
            else:
                raise ValueError(f"Unsupported credential service URI scheme: {uri}")
        except Exception as e:
            raise ValueError(f"Failed to parse credential service URI '{uri}': {e}")

    def _parse_google_oauth2_uri(self, uri: str) -> BaseCredentialService:
        """Parse Google OAuth2 URI: oauth2-google://client-id:secret@scopes=scope1,scope2"""
        from .credentials.google_oauth2_credential_service import (
            GoogleOAuth2CredentialService,
        )
        # Remove scheme
        uri_part = uri[len("oauth2-google://"):]
        
        # Split at @
        if "@" in uri_part:
            credentials_part, params_part = uri_part.split("@", 1)
        else:
            credentials_part = uri_part
            params_part = ""
        
        # Parse credentials
        if ":" in credentials_part:
            client_id, client_secret = credentials_part.split(":", 1)
        else:
            raise ValueError("Google OAuth2 URI must include client_id:client_secret")
        
        # Parse parameters
        scopes = []
        if params_part:
            for param in params_part.split("&"):
                if param.startswith("scopes="):
                    scopes = param[7:].split(",")
        
        return GoogleOAuth2CredentialService(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["openid", "email", "profile"]
        )

    def _parse_github_oauth2_uri(self, uri: str) -> BaseCredentialService:
        """Parse GitHub OAuth2 URI: oauth2-github://client-id:secret@scopes=user,repo"""
        from .credentials.github_oauth2_credential_service import (
            GitHubOAuth2CredentialService,
        )
        uri_part = uri[len("oauth2-github://"):]
        
        if "@" in uri_part:
            credentials_part, params_part = uri_part.split("@", 1)
        else:
            credentials_part = uri_part
            params_part = ""
        
        if ":" in credentials_part:
            client_id, client_secret = credentials_part.split(":", 1)
        else:
            raise ValueError("GitHub OAuth2 URI must include client_id:client_secret")
        
        scopes = []
        if params_part:
            for param in params_part.split("&"):
                if param.startswith("scopes="):
                    scopes = param[7:].split(",")
        
        return GitHubOAuth2CredentialService(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["user"]
        )

    def _parse_microsoft_oauth2_uri(self, uri: str) -> BaseCredentialService:
        """Parse Microsoft OAuth2 URI: oauth2-microsoft://tenant-id/client-id:secret@scopes=User.Read"""
        from .credentials.microsoft_oauth2_credential_service import (
            MicrosoftOAuth2CredentialService,
        )
        uri_part = uri[len("oauth2-microsoft://"):]
        
        if "@" in uri_part:
            credentials_part, params_part = uri_part.split("@", 1)
        else:
            credentials_part = uri_part
            params_part = ""
        
        # Parse tenant_id/client_id:secret
        if "/" in credentials_part:
            tenant_part, client_part = credentials_part.split("/", 1)
        else:
            raise ValueError("Microsoft OAuth2 URI must include tenant-id/client-id:secret")
        
        if ":" in client_part:
            client_id, client_secret = client_part.split(":", 1)
        else:
            raise ValueError("Microsoft OAuth2 URI must include client_id:client_secret")
        
        scopes = []
        if params_part:
            for param in params_part.split("&"):
                if param.startswith("scopes="):
                    scopes = param[7:].split(",")
        
        return MicrosoftOAuth2CredentialService(
            tenant_id=tenant_part,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["User.Read"]
        )

    def _parse_x_oauth2_uri(self, uri: str) -> BaseCredentialService:
        """Parse X OAuth2 URI: oauth2-x://client-id:secret@scopes=tweet.read,users.read"""
        from .credentials.x_oauth2_credential_service import XOAuth2CredentialService
        uri_part = uri[len("oauth2-x://"):]
        
        if "@" in uri_part:
            credentials_part, params_part = uri_part.split("@", 1)
        else:
            credentials_part = uri_part
            params_part = ""
        
        if ":" in credentials_part:
            client_id, client_secret = credentials_part.split(":", 1)
        else:
            raise ValueError("X OAuth2 URI must include client_id:client_secret")
        
        scopes = []
        if params_part:
            for param in params_part.split("&"):
                if param.startswith("scopes="):
                    scopes = param[7:].split(",")
        
        return XOAuth2CredentialService(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or ["tweet.read", "users.read", "offline.access"]
        )

    def _parse_jwt_uri(self, uri: str) -> BaseCredentialService:
        """Parse JWT URI: jwt://secret@algorithm=HS256&issuer=my-app&audience=api.example.com&expiration_minutes=60"""
        from .credentials.jwt_credential_service import JWTCredentialService
        uri_part = uri[len("jwt://"):]
        
        if "@" in uri_part:
            secret, params_part = uri_part.split("@", 1)
        else:
            secret = uri_part
            params_part = ""
        
        # Parse parameters
        algorithm = "HS256"
        issuer = None
        audience = None
        expiration_minutes = 60
        custom_claims = {}
        
        if params_part:
            for param in params_part.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key == "algorithm":
                        algorithm = value
                    elif key == "issuer":
                        issuer = value
                    elif key == "audience":
                        audience = value
                    elif key == "expiration_minutes":
                        expiration_minutes = int(value)
                    else:
                        # Custom claim
                        custom_claims[key] = value
        
        return JWTCredentialService(
            secret=secret,
            algorithm=algorithm,
            issuer=issuer,
            audience=audience,
            expiration_minutes=expiration_minutes,
            custom_claims=custom_claims
        )

    def _parse_basic_auth_uri(self, uri: str) -> BaseCredentialService:
        """Parse Basic Auth URI: basic-auth://username:password@realm=My API"""
        from .credentials.http_basic_auth_credential_service import (
            HTTPBasicAuthCredentialService,
        )
        uri_part = uri[len("basic-auth://"):]
        
        if "@" in uri_part:
            credentials_part, params_part = uri_part.split("@", 1)
        else:
            credentials_part = uri_part
            params_part = ""
        
        if ":" in credentials_part:
            username, password = credentials_part.split(":", 1)
        else:
            raise ValueError("Basic Auth URI must include username:password")
        
        realm = None
        if params_part:
            for param in params_part.split("&"):
                if param.startswith("realm="):
                    realm = param[6:]
        
        return HTTPBasicAuthCredentialService(
            username=username,
            password=password,
            realm=realm
        )

    # Build methods
    def build_fastapi_app(self) -> FastAPI:
        """Build and return configured FastAPI application.
        
        Returns:
            FastAPI: Configured FastAPI application with all ADK features.
            
        Raises:
            ValueError: If required configuration is missing.
        """
        # Create services (agent loader validates agent configuration)
        agent_loader = self._create_agent_loader()
        session_service = self._create_session_service()
        artifact_service = self._create_artifact_service()
        memory_service = self._create_memory_service()
        credential_service = self._create_credential_service()
        
        # Initialize credential service if it's one of ours
        if isinstance(credential_service, BaseCustomCredentialService):
            import asyncio
            try:
                # Try to initialize in current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a task for initialization
                    asyncio.create_task(credential_service.initialize())
                else:
                    loop.run_until_complete(credential_service.initialize())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(credential_service.initialize())
        
        # Use our enhanced FastAPI function that properly supports credential services
        logger.info("Building FastAPI app with enhanced credential service support")
        
        # Import our enhanced function
        from .enhanced_fastapi import get_enhanced_fast_api_app
        
        app = get_enhanced_fast_api_app(
            agents_dir=self._agents_dir,
            agent_loader=agent_loader,
            session_service_uri=self._session_service_uri,
            session_db_kwargs=self._session_db_kwargs,
            artifact_service_uri=self._artifact_service_uri,
            memory_service_uri=self._memory_service_uri,
            credential_service=credential_service,  # May be None; server will default
            eval_storage_uri=self._eval_storage_uri,
            allow_origins=self._allow_origins,
            web=self._web_ui,
            a2a=self._a2a,
            programmatic_a2a=self._a2a_expose_programmatic,
            programmatic_a2a_mount_base=self._a2a_programmatic_mount_base,
            programmatic_a2a_card_factory=self._a2a_card_factory,
            host=self._host,
            port=self._port,
            trace_to_cloud=self._trace_to_cloud,
            reload_agents=self._reload_agents,
            lifespan=self._lifespan,
        )
        
        return app

    def build_runner(self, agent_or_agent_name: Union[BaseAgent, str]) -> Runner:
        """Build and return configured Runner.
        
        Args:
            agent_or_agent_name: Agent instance or agent name to load.
            
        Returns:
            Runner: Configured Runner instance.
            
        Raises:
            ValueError: If required configuration is missing.
        """
        # Resolve agent instance
        if isinstance(agent_or_agent_name, str):
            name = agent_or_agent_name
            agent = None
            # 1) Prefer explicitly provided custom loader (supports programmatic agents)
            if self._agent_loader is not None:
                try:
                    agent = self._agent_loader.load_agent(name)
                except Exception:
                    agent = None
            # 2) Try registered agents collected via with_agent_instance()/with_agents()
            if agent is None and self._registered_agents:
                agent = self._registered_agents.get(name)
            # 3) Fallback to directory-based AgentLoader if agents_dir is set
            if agent is None and self._agents_dir:
                agent = AgentLoader(self._agents_dir).load_agent(name)
            if agent is None:
                raise ValueError(
                    "Agent not found. Provide an instance via with_agent_instance()/with_agents(), "
                    "or set a custom loader with with_agent_loader(), or set with_agents_dir() for directory-based loading."
                )
        else:
            agent = agent_or_agent_name
        
        # Create services
        session_service = self._create_session_service()
        artifact_service = self._create_artifact_service()
        memory_service = self._create_memory_service()
        credential_service = self._create_credential_service()
        
        # Initialize credential service if it's one of ours
        if isinstance(credential_service, BaseCustomCredentialService):
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(credential_service.initialize())
                else:
                    loop.run_until_complete(credential_service.initialize())
            except RuntimeError:
                asyncio.run(credential_service.initialize())
        
        # Create Runner with all services
        app_name = self._app_name or (agent_or_agent_name if isinstance(agent_or_agent_name, str) else "default_app")
        
        return Runner(
            app_name=app_name,
            agent=agent,
            session_service=session_service,
            artifact_service=artifact_service,
            memory_service=memory_service,
            credential_service=credential_service,
        )
