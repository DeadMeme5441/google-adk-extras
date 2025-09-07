"""Enhanced FastAPI app creation with credential service support.

This module provides an enhanced version of Google ADK's get_fast_api_app function
that properly supports custom credential services.
"""

import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Mapping, Optional, List, Callable, Dict

import click
from fastapi import FastAPI
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.responses import PlainTextResponse
from starlette.types import Lifespan
from watchdog.observers import Observer

from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.auth.credential_service.base_credential_service import BaseCredentialService
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.evaluation.local_eval_sets_manager import LocalEvalSetsManager
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.utils.feature_decorator import working_in_progress
from google.adk.cli.adk_web_server import AdkWebServer
from .enhanced_adk_web_server import EnhancedAdkWebServer
from google.adk.cli.utils import envs
from google.adk.cli.utils import evals
from google.adk.cli.utils.agent_change_handler import AgentChangeEventHandler
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader

logger = logging.getLogger(__name__)


def get_enhanced_fast_api_app(
    *,
    agents_dir: Optional[str] = None,
    agent_loader: Optional[BaseAgentLoader] = None,
    session_service_uri: Optional[str] = None,
    session_db_kwargs: Optional[Mapping[str, Any]] = None,
    artifact_service_uri: Optional[str] = None,
    memory_service_uri: Optional[str] = None,
    credential_service: Optional[BaseCredentialService] = None,  # Optional credential service
    eval_storage_uri: Optional[str] = None,
    allow_origins: Optional[List[str]] = None,
    web: bool = True,
    a2a: bool = False,
    programmatic_a2a: bool = False,
    programmatic_a2a_mount_base: str = "/a2a",
    programmatic_a2a_card_factory: Optional[Callable[[str, Any], Dict[str, Any]]] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    trace_to_cloud: bool = False,
    reload_agents: bool = False,
    lifespan: Optional[Lifespan[FastAPI]] = None,
) -> FastAPI:
    """Enhanced version of Google ADK's get_fast_api_app with EnhancedRunner integration.
    
    This function extends Google ADK's get_fast_api_app with enhanced capabilities:
    1. Uses EnhancedAdkWebServer which creates EnhancedRunner instances
    2. Supports custom credential services instead of hardcoding InMemoryCredentialService
    3. Supports custom agent loading logic
    4. Provides advanced tool execution strategies (MCP, OpenAPI, Function tools)
    5. Enables circuit breakers, retry policies, and performance monitoring
    6. Supports YAML-driven configuration and error context
    
    Args:
        agents_dir: Directory containing agent definitions (optional if agent_loader provided).
        agent_loader: Custom agent loader instance (optional if agents_dir provided).
        session_service_uri: Session service URI.
        session_db_kwargs: Additional database configuration for session service.
        artifact_service_uri: Artifact service URI.
        memory_service_uri: Memory service URI.
        credential_service: Custom credential service instance.
        eval_storage_uri: Evaluation storage URI.
        allow_origins: CORS allowed origins.
        web: Whether to serve web UI.
        a2a: Whether to enable A2A protocol.
        host: Server host.
        port: Server port.
        trace_to_cloud: Whether to enable cloud tracing.
        reload_agents: Whether to enable hot reloading.
        lifespan: FastAPI lifespan callable.
        (Enhanced runner options removed for simplified scope.)
        
    Returns:
        FastAPI: Configured FastAPI application.
        
    Raises:
        ValueError: If neither agents_dir nor agent_loader is provided.
    """
    # Validate agent configuration
    if not agent_loader and not agents_dir:
        raise ValueError("Either agent_loader or agents_dir must be provided")
    
    # Create or use provided agent loader
    if agent_loader is not None:
        final_agent_loader = agent_loader
        # Try to extract agents_dir from AgentLoader for compatibility
        if agents_dir is None and hasattr(agent_loader, 'agents_dir'):
            agents_dir = agent_loader.agents_dir
        elif agents_dir is None:
            # For non-directory loaders, create a temp dir for eval managers
            import tempfile
            agents_dir = tempfile.gettempdir()
    else:
        final_agent_loader = AgentLoader(agents_dir)
    
    logger.info("Using agent loader: %s", type(final_agent_loader).__name__)
    
    # Set up eval managers (same as ADK)
    if eval_storage_uri:
        gcs_eval_managers = evals.create_gcs_eval_managers_from_uri(eval_storage_uri)
        eval_sets_manager = gcs_eval_managers.eval_sets_manager
        eval_set_results_manager = gcs_eval_managers.eval_set_results_manager
    else:
        eval_sets_manager = LocalEvalSetsManager(agents_dir=agents_dir)
        eval_set_results_manager = LocalEvalSetResultsManager(agents_dir=agents_dir)

    def _parse_agent_engine_resource_name(agent_engine_id_or_resource_name):
        """Parse agent engine resource name (same as ADK)."""
        if not agent_engine_id_or_resource_name:
            raise click.ClickException(
                "Agent engine resource name or resource id can not be empty."
            )

        if "/" in agent_engine_id_or_resource_name:
            if len(agent_engine_id_or_resource_name.split("/")) != 6:
                raise click.ClickException(
                    "Agent engine resource name is mal-formatted. It should be of"
                    " format: projects/{project_id}/locations/{location}/reasoningEngines/{resource_id}"
                )
            project = agent_engine_id_or_resource_name.split("/")[1]
            location = agent_engine_id_or_resource_name.split("/")[3]
            agent_engine_id = agent_engine_id_or_resource_name.split("/")[-1]
        else:
            envs.load_dotenv_for_agent("", agents_dir)
            project = os.environ["GOOGLE_CLOUD_PROJECT"]
            location = os.environ["GOOGLE_CLOUD_LOCATION"]
            agent_engine_id = agent_engine_id_or_resource_name
        return project, location, agent_engine_id

    # Build the Memory service (same as ADK)
    if memory_service_uri:
        if memory_service_uri.startswith("rag://"):
            from google.adk.memory.vertex_ai_rag_memory_service import VertexAiRagMemoryService
            rag_corpus = memory_service_uri.split("://")[1]
            if not rag_corpus:
                raise click.ClickException("Rag corpus can not be empty.")
            envs.load_dotenv_for_agent("", agents_dir)
            memory_service = VertexAiRagMemoryService(
                rag_corpus=f'projects/{os.environ["GOOGLE_CLOUD_PROJECT"]}/locations/{os.environ["GOOGLE_CLOUD_LOCATION"]}/ragCorpora/{rag_corpus}'
            )
        elif memory_service_uri.startswith("agentengine://"):
            agent_engine_id_or_resource_name = memory_service_uri.split("://")[1]
            project, location, agent_engine_id = _parse_agent_engine_resource_name(
                agent_engine_id_or_resource_name
            )
            memory_service = VertexAiMemoryBankService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
        else:
            raise click.ClickException(
                "Unsupported memory service URI: %s" % memory_service_uri
            )
    else:
        memory_service = InMemoryMemoryService()

    # Build the Session service (same as ADK)
    if session_service_uri:
        if session_service_uri.startswith("agentengine://"):
            agent_engine_id_or_resource_name = session_service_uri.split("://")[1]
            project, location, agent_engine_id = _parse_agent_engine_resource_name(
                agent_engine_id_or_resource_name
            )
            session_service = VertexAiSessionService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
        else:
            # Database session additional settings
            if session_db_kwargs is None:
                session_db_kwargs = {}
            session_service = DatabaseSessionService(
                db_url=session_service_uri, **session_db_kwargs
            )
    else:
        session_service = InMemorySessionService()

    # Build the Artifact service (same as ADK)
    if artifact_service_uri:
        if artifact_service_uri.startswith("gs://"):
            gcs_bucket = artifact_service_uri.split("://")[1]
            artifact_service = GcsArtifactService(bucket_name=gcs_bucket)
        else:
            raise click.ClickException(
                "Unsupported artifact service URI: %s" % artifact_service_uri
            )
    else:
        artifact_service = InMemoryArtifactService()

    # Credential service is optional; EnhancedAdkWebServer will default if needed
    credential_service_instance = credential_service
    if credential_service_instance is None:
        logger.info("No credential service provided; server will use its default")

    # Use configured agent loader (enhanced from ADK)

    # Create EnhancedAdkWebServer with our custom credential service and enhanced features
    adk_web_server = EnhancedAdkWebServer(
        # Standard ADK parameters
        agent_loader=final_agent_loader,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
        credential_service=credential_service_instance,  # Use our custom service
        eval_sets_manager=eval_sets_manager,
        eval_set_results_manager=eval_set_results_manager,
        agents_dir=agents_dir,
    )

    # Callbacks & other optional args for FastAPI instance (same as ADK)
    extra_fast_api_args = {}

    if trace_to_cloud:
        logger.warning(
            "trace_to_cloud requested but OpenTelemetry exporters are not bundled. "
            "Tracing is disabled."
        )

    if reload_agents:
        def setup_observer(observer: Observer, adk_web_server: AdkWebServer):
            agent_change_handler = AgentChangeEventHandler(
                agent_loader=final_agent_loader,
                runners_to_clean=adk_web_server.runners_to_clean,
                current_app_name_ref=adk_web_server.current_app_name_ref,
            )
            observer.schedule(agent_change_handler, agents_dir, recursive=True)
            observer.start()

        def tear_down_observer(observer: Observer, _: AdkWebServer):
            observer.stop()
            observer.join()

        extra_fast_api_args.update(
            setup_observer=setup_observer,
            tear_down_observer=tear_down_observer,
        )

    if web:
        try:
            # Try to find ADK's web assets
            from google.adk.cli.fast_api import BASE_DIR
            ANGULAR_DIST_PATH = BASE_DIR / "browser"
        except (ImportError, AttributeError):
            # Fallback if ADK structure changes
            BASE_DIR = Path(__file__).parent.resolve()
            ANGULAR_DIST_PATH = BASE_DIR / "browser"
        
        if ANGULAR_DIST_PATH.exists():
            extra_fast_api_args.update(web_assets_dir=ANGULAR_DIST_PATH)
        else:
            logger.warning("Web UI assets not found, web interface will not be available")

    # Create FastAPI app
    app = adk_web_server.get_fast_api_app(
        lifespan=lifespan,
        allow_origins=allow_origins,
        **extra_fast_api_args,
    )
    
    # Store the ADK web server in app state for testing access
    app.state.adk_web_server = adk_web_server

    # Add additional endpoints that ADK normally adds
    @working_in_progress("builder_save is not ready for use.")
    @app.post("/builder/save", response_model_exclude_none=True)
    async def builder_build(files: List[UploadFile]) -> bool:
        base_path = Path.cwd() / agents_dir
        for file in files:
            try:
                if not file.filename:
                    logger.exception("Agent name is missing in the input files")
                    return False
                agent_name, filename = file.filename.split("/")
                agent_dir = os.path.join(base_path, agent_name)
                os.makedirs(agent_dir, exist_ok=True)
                file_path = os.path.join(agent_dir, filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            except Exception as e:
                logger.exception("Error in builder_build: %s", e)
                return False
        return True

    @working_in_progress("builder_get is not ready for use.")
    @app.get(
        "/builder/app/{app_name}",
        response_model_exclude_none=True,
        response_class=PlainTextResponse,
    )
    async def get_agent_builder(app_name: str, file_path: Optional[str] = None):
        base_path = Path.cwd() / agents_dir
        agent_dir = base_path / app_name
        if not file_path:
            file_name = "root_agent.yaml"
            root_file_path = agent_dir / file_name
            if not root_file_path.is_file():
                return ""
            else:
                return FileResponse(
                    path=root_file_path,
                    media_type="application/x-yaml",
                    filename=f"{app_name}.yaml",
                    headers={"Cache-Control": "no-store"},
                )
        else:
            agent_file_path = agent_dir / file_path
            if not agent_file_path.is_file():
                return ""
            else:
                return FileResponse(
                    path=agent_file_path,
                    media_type="application/x-yaml",
                    filename=file_path,
                    headers={"Cache-Control": "no-store"},
                )

    # A2A protocol support (same as ADK)
    if a2a:
        try:
            from a2a.server.apps import A2AStarletteApplication
            from a2a.server.request_handlers import DefaultRequestHandler
            from a2a.server.tasks import InMemoryTaskStore
            from a2a.types import AgentCard
            from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
            from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

        except ImportError as e:
            import sys
            if sys.version_info < (3, 12):
                raise ImportError(
                    "A2A requires Python 3.12 or above. Please upgrade your Python version."
                ) from e
            else:
                raise e

        a2a_task_store = InMemoryTaskStore()

        def create_a2a_runner_loader(captured_app_name: str):
            async def _get_a2a_runner_async() -> Runner:
                return await adk_web_server.get_runner_async(captured_app_name)
            return _get_a2a_runner_async

        # 1) Directory-based A2A (existing behavior)
        if agents_dir:
            base_path = Path.cwd() / agents_dir
            if base_path.exists() and base_path.is_dir():
                for p in base_path.iterdir():
                    try:
                        if (
                            p.is_file()
                            or p.name.startswith((".", "__pycache__"))
                            or not (p / "agent.json").is_file()
                        ):
                            continue
                    except PermissionError:
                        # Skip directories we cannot inspect
                        continue

                    app_name = p.name
                    logger.info("Setting up A2A agent (dir): %s", app_name)

                    try:
                        agent_executor = A2aAgentExecutor(
                            runner=create_a2a_runner_loader(app_name),
                        )
                        request_handler = DefaultRequestHandler(
                            agent_executor=agent_executor, task_store=a2a_task_store
                        )
                        with (p / "agent.json").open("r", encoding="utf-8") as f:
                            data = json.load(f)
                            agent_card = AgentCard(**data)
                        a2a_app = A2AStarletteApplication(
                            agent_card=agent_card,
                            http_handler=request_handler,
                        )
                        routes = a2a_app.routes(
                            rpc_url=f"/a2a/{app_name}",
                            agent_card_url=f"/a2a/{app_name}{AGENT_CARD_WELL_KNOWN_PATH}",
                        )
                        for new_route in routes:
                            app.router.routes.append(new_route)
                        logger.info("Configured A2A agent (dir): %s", app_name)
                    except Exception as e:
                        logger.error("Failed to setup A2A agent %s: %s", app_name, e)

        # 2) Programmatic A2A for registered agents (no agents_dir)
        if programmatic_a2a:
            # Attempt to enumerate agents from the provided loader
            agent_names = []
            if hasattr(final_agent_loader, "list_agents"):
                try:
                    agent_names = final_agent_loader.list_agents()  # type: ignore[attr-defined]
                except Exception:
                    agent_names = []

            for app_name in agent_names:
                try:
                    agent_instance = final_agent_loader.load_agent(app_name)
                except Exception:
                    agent_instance = None

                logger.info("Setting up A2A agent (programmatic): %s", app_name)
                try:
                    # Construct AgentCard data
                    data: Dict[str, Any]
                    if programmatic_a2a_card_factory and agent_instance is not None:
                        try:
                            data = programmatic_a2a_card_factory(app_name, agent_instance)
                        except TypeError:
                            # Backward compatibility: factory taking only name
                            data = programmatic_a2a_card_factory(app_name)  # type: ignore[misc]
                    else:
                        # Minimal default card
                        data = {
                            "name": app_name,
                            "description": f"A2A-exposed agent {app_name}",
                            "defaultInputModes": ["text/plain"],
                            "defaultOutputModes": ["application/json"],
                            "version": "1.0.0",
                        }

                    agent_executor = A2aAgentExecutor(
                        runner=create_a2a_runner_loader(app_name),
                    )
                    request_handler = DefaultRequestHandler(
                        agent_executor=agent_executor, task_store=a2a_task_store
                    )
                    agent_card = AgentCard(**data)
                    a2a_app = A2AStarletteApplication(
                        agent_card=agent_card,
                        http_handler=request_handler,
                    )
                    routes = a2a_app.routes(
                        rpc_url=f"{programmatic_a2a_mount_base}/{app_name}",
                        agent_card_url=f"{programmatic_a2a_mount_base}/{app_name}{AGENT_CARD_WELL_KNOWN_PATH}",
                    )
                    for new_route in routes:
                        app.router.routes.append(new_route)
                    logger.info("Configured A2A agent (programmatic): %s", app_name)
                except Exception as e:
                    logger.error("Failed to setup programmatic A2A agent %s: %s", app_name, e)

    logger.info("Enhanced FastAPI app created with credential service support")
    return app
