"""Ensure CustomAgentLoader is compatible with ADK's hot-reload handler.

AgentChangeEventHandler expects `remove_agent_from_cache` on the loader.
This test verifies our no-op implementation exists and can be called by the
handler without exceptions when a file change is dispatched.
"""

from types import SimpleNamespace

from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google.adk.cli.utils.agent_change_handler import AgentChangeEventHandler


def test_custom_agent_loader_has_remove_agent_from_cache_and_handler_calls_it():
    loader = CustomAgentLoader()
    assert hasattr(loader, "remove_agent_from_cache")

    # Prepare the handler dependencies
    runners_to_clean = set()
    current_app_name_ref = SimpleNamespace(value="sample_app")

    handler = AgentChangeEventHandler(
        agent_loader=loader,
        runners_to_clean=runners_to_clean,
        current_app_name_ref=current_app_name_ref,
    )

    # Simulate a file modification event that should trigger invalidation
    event = SimpleNamespace(src_path="/tmp/agent.py")
    handler.on_modified(event)

    # The app name should be marked for cleanup by the handler
    assert "sample_app" in runners_to_clean

