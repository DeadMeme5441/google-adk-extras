"""Production-ready services and FastAPI wiring for Google ADK.

Public API surface:
- AdkBuilder
- get_enhanced_fast_api_app
- EnhancedAdkWebServer
- EnhancedRunner (thin wrapper over ADK Runner)
- CustomAgentLoader (programmatic agents)

Service groups are exposed via subpackages:
- google_adk_extras.sessions
- google_adk_extras.artifacts
- google_adk_extras.memory
  (credential services are provided by ADK; no custom extras here)
"""

from .adk_builder import AdkBuilder
from .enhanced_fastapi import get_enhanced_fast_api_app
from .enhanced_adk_web_server import EnhancedAdkWebServer
from .enhanced_runner import EnhancedRunner
from .custom_agent_loader import CustomAgentLoader

__all__ = [
    "AdkBuilder",
    "get_enhanced_fast_api_app",
    "EnhancedAdkWebServer",
    "EnhancedRunner",
    "CustomAgentLoader",
]

__version__ = "0.3.3"
