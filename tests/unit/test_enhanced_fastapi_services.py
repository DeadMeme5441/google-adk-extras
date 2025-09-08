"""Tests for enhanced_fastapi service construction from URIs.

We patch EnhancedAdkWebServer to capture constructed service instances
without invoking the real ADK server, and verify that yaml://, local://, and
sqlite:// URIs produce the expected implementations.
"""

import tempfile
from unittest.mock import patch, MagicMock

import pytest

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app


@patch("google_adk_extras.enhanced_fastapi.EnhancedAdkWebServer")
def test_memory_yaml_and_artifact_local_and_session_yaml(mock_server):
    # Prepare mock server to return a dummy FastAPI app-like object
    mock_server_instance = MagicMock()
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_server_instance.get_fast_api_app.return_value = mock_app
    mock_server.return_value = mock_server_instance

    with tempfile.TemporaryDirectory() as tmp:
        # URIs to exercise yaml/local mapping
        mem_uri = f"yaml://{tmp}/memory"
        art_uri = f"local://{tmp}/artifacts"
        sess_uri = f"yaml://{tmp}/sessions"

        # Use a trivial loader path by providing an agents_dir; the server is mocked
        app = get_enhanced_fast_api_app(
            agents_dir=tmp,
            memory_service_uri=mem_uri,
            artifact_service_uri=art_uri,
            session_service_uri=sess_uri,
            web=False,
        )

        assert app is mock_app

        # Inspect constructed services passed to EnhancedAdkWebServer
        call_kwargs = mock_server.call_args.kwargs
        mem_service = call_kwargs["memory_service"]
        art_service = call_kwargs["artifact_service"]
        sess_service = call_kwargs["session_service"]

        from google_adk_extras.memory.yaml_file_memory_service import (
            YamlFileMemoryService,
        )
        from google_adk_extras.artifacts.local_folder_artifact_service import (
            LocalFolderArtifactService,
        )
        from google_adk_extras.sessions.yaml_file_session_service import (
            YamlFileSessionService,
        )

        assert isinstance(mem_service, YamlFileMemoryService)
        assert isinstance(art_service, LocalFolderArtifactService)
        assert isinstance(sess_service, YamlFileSessionService)


@patch("google_adk_extras.enhanced_fastapi.EnhancedAdkWebServer")
def test_session_sqlite_still_uses_database_session_service(mock_server):
    """Non-agentengine session_service_uri falls back to ADK DatabaseSessionService."""
    mock_server_instance = MagicMock()
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_server_instance.get_fast_api_app.return_value = mock_app
    mock_server.return_value = mock_server_instance

    with tempfile.TemporaryDirectory() as tmp:
        sess_uri = "sqlite:///" + tmp + "/sessions.db"

        _ = get_enhanced_fast_api_app(
            agents_dir=tmp,
            session_service_uri=sess_uri,
            web=False,
        )

        call_kwargs = mock_server.call_args.kwargs
        sess_service = call_kwargs["session_service"]

        # Avoid cross-import aliasing issues in test harness by checking module path
        assert type(sess_service).__module__.startswith(
            "google.adk.sessions.database_session_service"
        )


@patch("google_adk_extras.enhanced_fastapi.EnhancedAdkWebServer")
@pytest.mark.skipif("sqlalchemy" not in [m.name for m in list(__import__("pkgutil").iter_modules())], reason="SQLAlchemy not available")
def test_memory_sqlite_uses_sql_memory_service(mock_server):
    """If SQLAlchemy is available, sqlite memory URI maps to SQLMemoryService."""
    mock_server_instance = MagicMock()
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_server_instance.get_fast_api_app.return_value = mock_app
    mock_server.return_value = mock_server_instance

    with tempfile.TemporaryDirectory() as tmp:
        mem_uri = "sqlite:///" + tmp + "/memory.db"

        _ = get_enhanced_fast_api_app(
            agents_dir=tmp,
            memory_service_uri=mem_uri,
            web=False,
        )

        call_kwargs = mock_server.call_args.kwargs
        mem_service = call_kwargs["memory_service"]

        from google_adk_extras.memory.sql_memory_service import SQLMemoryService

        assert isinstance(mem_service, SQLMemoryService)
