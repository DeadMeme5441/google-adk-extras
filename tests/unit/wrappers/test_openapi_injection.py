from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from unittest.mock import patch, MagicMock
import tempfile

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app


def make_stub_adk_app():
    app = FastAPI()

    @app.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
    def get_session(app_name: str, user_id: str, session_id: str):
        return {"id": session_id, "appName": app_name, "userId": user_id, "events": [], "lastUpdateTime": 0.0}

    @app.get("/apps/{app_name}/users/{user_id}/sessions")
    def list_sessions(app_name: str, user_id: str):
        return []

    @app.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts")
    def list_artifacts(app_name: str, user_id: str, session_id: str):
        return []

    return app


@patch("google_adk_extras.enhanced_fastapi.EnhancedAdkWebServer")
def test_openapi_params_injected(mock_server):
    # Return the stubbed FastAPI app from the server
    mock_server_instance = MagicMock()
    mock_app = make_stub_adk_app()
    mock_server_instance.get_fast_api_app.return_value = mock_app
    mock_server.return_value = mock_server_instance

    with tempfile.TemporaryDirectory() as tmp:
        app = get_enhanced_fast_api_app(agents_dir=tmp, web=False)
        schema = app.openapi()
        # Validate a few representative params exist
        sess_get = schema["paths"]["/apps/{app_name}/users/{user_id}/sessions/{session_id}"]["get"]["parameters"]
        names = {p["name"] for p in sess_get}
        assert {"events_limit", "include_event_fields", "include_part_types"}.issubset(names)

        sess_list = schema["paths"]["/apps/{app_name}/users/{user_id}/sessions"]["get"]["parameters"]
        names2 = {p["name"] for p in sess_list}
        assert {"updated_after_ts", "id_prefix", "limit"}.issubset(names2)

        art_list = schema["paths"]["/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts"]["get"]["parameters"]
        names3 = {p["name"] for p in art_list}
        assert {"prefix", "after_name", "limit"}.issubset(names3)

