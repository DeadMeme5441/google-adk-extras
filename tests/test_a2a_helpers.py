import sys
import types
from typing import Any, Dict

import pytest


def _install_stub(path: str, **attrs):
    mod = types.ModuleType(path)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[path] = mod
    return mod


def _install_adk_a2a_stubs():
    # Ensure root namespace exists for stubbed modules
    if "google" not in sys.modules:
        sys.modules["google"] = types.ModuleType("google")
    if "google.adk" not in sys.modules:
        sys.modules["google.adk"] = types.ModuleType("google.adk")
    # Minimal ADK classes used at import-time
    _install_stub(
        "google.adk.artifacts.gcs_artifact_service",
        GcsArtifactService=type("GcsArtifactService", (), {})
    )
    _install_stub(
        "google.adk.artifacts.in_memory_artifact_service",
        InMemoryArtifactService=type("InMemoryArtifactService", (), {})
    )
    _install_stub(
        "google.adk.auth.credential_service.in_memory_credential_service",
        InMemoryCredentialService=type("InMemoryCredentialService", (), {})
    )
    _install_stub(
        "google.adk.auth.credential_service.base_credential_service",
        BaseCredentialService=type("BaseCredentialService", (), {})
    )
    _install_stub(
        "google.adk.evaluation.local_eval_set_results_manager",
        LocalEvalSetResultsManager=type("LocalEvalSetResultsManager", (), {})
    )
    _install_stub(
        "google.adk.evaluation.local_eval_sets_manager",
        LocalEvalSetsManager=type("LocalEvalSetsManager", (), {})
    )
    _install_stub(
        "google.adk.memory.in_memory_memory_service",
        InMemoryMemoryService=type("InMemoryMemoryService", (), {})
    )
    _install_stub(
        "google.adk.memory.vertex_ai_memory_bank_service",
        VertexAiMemoryBankService=type("VertexAiMemoryBankService", (), {})
    )
    _install_stub(
        "google.adk.sessions.in_memory_session_service",
        InMemorySessionService=type("InMemorySessionService", (), {})
    )
    _install_stub(
        "google.adk.sessions.vertex_ai_session_service",
        VertexAiSessionService=type("VertexAiSessionService", (), {})
    )
    _install_stub(
        "google.adk.sessions.database_session_service",
        DatabaseSessionService=type("DatabaseSessionService", (), {})
    )
    _install_stub(
        "google.adk.utils.feature_decorator",
        working_in_progress=lambda _: (lambda f: f)
    )
    # Do not stub google.adk.cli.adk_web_server to avoid clashing with other tests
    _install_stub("google.adk.cli.utils.envs")
    _install_stub("google.adk.cli.utils.evals")
    _install_stub(
        "google.adk.cli.utils.agent_change_handler",
        AgentChangeEventHandler=type("AgentChangeEventHandler", (), {})
    )
    _install_stub(
        "google.adk.cli.utils.agent_loader",
        AgentLoader=type("AgentLoader", (), {})
    )
    _install_stub(
        "google.adk.cli.utils.base_agent_loader",
        BaseAgentLoader=type("BaseAgentLoader", (), {})
    )
    _install_stub(
        "google.adk.runners",
        Runner=type("Runner", (), {})
    )
    _install_stub(
        "google.adk.agents.base_agent",
        BaseAgent=type("BaseAgent", (), {})
    )
    _install_stub(
        "google.adk.sessions.base_session_service",
        BaseSessionService=type("BaseSessionService", (), {})
    )
    _install_stub(
        "google.adk.artifacts.base_artifact_service",
        BaseArtifactService=type("BaseArtifactService", (), {})
    )
    _install_stub(
        "google.adk.memory.base_memory_service",
        BaseMemoryService=type("BaseMemoryService", (), {})
    )
    # A2A stubs
    class DummyRoute:
        def __init__(self, path: str):
            self.path = path

    class DummyA2AApp:
        def __init__(self, agent_card: Any, http_handler: Any):
            self.agent_card = agent_card
            self.http_handler = http_handler

        def routes(self, rpc_url: str, agent_card_url: str):
            return [DummyRoute(rpc_url), DummyRoute(agent_card_url)]

    _install_stub(
        "a2a.server.apps",
        A2AStarletteApplication=DummyA2AApp
    )
    class _Handler:
        def __init__(self, *, agent_executor, task_store):
            self.agent_executor = agent_executor
            self.task_store = task_store
    _install_stub(
        "a2a.server.request_handlers",
        DefaultRequestHandler=_Handler
    )
    _install_stub(
        "a2a.server.tasks",
        InMemoryTaskStore=type("InMemoryTaskStore", (), {})
    )
    _install_stub(
        "a2a.types",
        AgentCard=type("AgentCard", (), {"__init__": lambda self, **_: None})
    )
    _install_stub(
        "a2a.utils.constants",
        AGENT_CARD_WELL_KNOWN_PATH="/.well-known/agent.json"
    )
    class _Exec:
        def __init__(self, *, runner):
            self.runner = runner
    _install_stub(
        "google.adk.a2a.executor.a2a_agent_executor",
        A2aAgentExecutor=_Exec,
    )


def test_programmatic_a2a_mounts_routes(tmp_path, monkeypatch):
    _install_adk_a2a_stubs()

    # Build a dummy loader with two agents
    class DummyLoader:
        def list_agents(self):
            return ["a1", "a2"]

        def load_agent(self, name: str):
            return object()

    from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app

    app = get_enhanced_fast_api_app(
        agent_loader=DummyLoader(),
        agents_dir=None,
        a2a=True,
        programmatic_a2a=True,
        programmatic_a2a_mount_base="/a2a",
    )

    paths = [getattr(r, "path", None) for r in app.router.routes]
    assert any(p == "/a2a/a1" for p in paths)
    assert any(p == "/a2a/a2" for p in paths)


def test_with_remote_a2a_agent_registers(monkeypatch):
    # Install RemoteA2aAgent stub under an expected path
    class RemoteA2aAgent:
        def __init__(self, name: str, description: str, agent_card: str):
            self.name = name
            self.description = description
            self.agent_card = agent_card

    mod = types.ModuleType("google.adk.a2a.remote_a2a_agent")
    mod.RemoteA2aAgent = RemoteA2aAgent
    sys.modules["google.adk.a2a.remote_a2a_agent"] = mod

    from google_adk_extras.adk_builder import AdkBuilder

    b = AdkBuilder().with_remote_a2a_agent(
        name="remote_prime",
        agent_card_url="http://host/a2a/prime/.well-known/agent.json",
        description="Prime checker",
    )

    # Access private registry via attribute for verification
    assert "remote_prime" in b._registered_agents
