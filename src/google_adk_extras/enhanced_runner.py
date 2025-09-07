"""Thin wrapper over google.adk.runners.Runner.

EnhancedRunner exists for compatibility with this package’s FastAPI server
integration. It does not add behavior beyond the base ADK Runner.
"""

from typing import List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts.base_artifact_service import BaseArtifactService
from google.adk.auth.credential_service.base_credential_service import BaseCredentialService
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.memory.base_memory_service import BaseMemoryService


class EnhancedRunner(Runner):
    def __init__(
        self,
        *,
        app_name: str,
        agent: BaseAgent,
        plugins: Optional[List[BasePlugin]] = None,
        artifact_service: Optional[BaseArtifactService] = None,
        session_service: BaseSessionService,
        memory_service: Optional[BaseMemoryService] = None,
        credential_service: Optional[BaseCredentialService] = None,
    ):
        super().__init__(
            app_name=app_name,
            agent=agent,
            plugins=plugins,
            artifact_service=artifact_service,
            session_service=session_service,
            memory_service=memory_service,
            credential_service=credential_service,
        )
