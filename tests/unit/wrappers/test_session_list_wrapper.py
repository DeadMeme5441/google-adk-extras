import json
from datetime import datetime

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from google_adk_extras.wrappers.session_list_wrapper import SessionListWrapperMiddleware


def make_app(sessions):
    async def list_sessions(request):
        return JSONResponse(sessions)

    return Starlette(routes=[Route("/apps/app/users/u/sessions", list_sessions)])


def sample_sessions():
    t = datetime.now().timestamp()
    return [
        {"id": "s1", "appName": "app", "userId": "u", "lastUpdateTime": t - 10, "events": []},
        {"id": "s2", "appName": "app", "userId": "u", "lastUpdateTime": t - 5, "events": []},
        {"id": "proj_alpha", "appName": "app", "userId": "u", "lastUpdateTime": t - 1, "events": []},
    ]


def test_list_sessions_filters_and_projection():
    sessions = sample_sessions()
    app = make_app(sessions)
    app.add_middleware(SessionListWrapperMiddleware)
    client = TestClient(app)
    r = client.get(
        "/apps/app/users/u/sessions",
        params={
            "id_prefix": "s",
            "updated_after_ts": str(sessions[0]["lastUpdateTime"] + 1),
            "fields": "id,lastUpdateTime",
            "sort": "last_update_time_desc",
            "limit": "1",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert set(body[0].keys()) == {"id", "lastUpdateTime"}
    assert body[0]["id"] == "s2"

