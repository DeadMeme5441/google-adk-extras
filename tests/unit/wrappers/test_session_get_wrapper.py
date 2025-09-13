import json
from datetime import datetime

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from google_adk_extras.wrappers.session_get_wrapper import SessionGetWrapperMiddleware


def make_app(session_payload):
    async def get_session(request):
        return JSONResponse(session_payload)

    routes = [
        Route("/apps/app/users/u/sessions/s1", get_session),
    ]
    app = Starlette(routes=routes)
    app.add_middleware(SessionGetWrapperMiddleware)
    return app


def sample_session():
    # Minimal realistic payload matching ADK alias keys
    ts = datetime.now().timestamp()
    return {
        "id": "s1",
        "appName": "app",
        "userId": "u",
        "state": {"x": 1},
        "lastUpdateTime": ts,
        "events": [
            {
                "id": "e1",
                "timestamp": ts - 5,
                "author": "user",
                "invocationId": "i1",
                "content": {"parts": [{"text": "Hello"}]},
                "actions": {"stateDelta": {}},
            },
            {
                "id": "e2",
                "timestamp": ts - 3,
                "author": "planner_agent",
                "invocationId": "i2",
                "content": {"parts": [{"functionCall": {"name": "plan"}}]},
                "actions": {"stateDelta": {"foo": 1}},
            },
            {
                "id": "e3",
                "timestamp": ts - 1,
                "author": "summarizer_agent",
                "invocationId": "i3",
                "partial": True,
                "content": {"parts": [{"text": "partial"}]},
                "actions": {"stateDelta": {}},
            },
        ],
    }


def test_top_level_projection_and_limit():
    app = make_app(sample_session())
    client = TestClient(app)
    r = client.get(
        "/apps/app/users/u/sessions/s1",
        params={
            "fields": "id,events,lastUpdateTime",
            "events_limit": "2",
            "include_event_fields": "id,timestamp,author",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"id", "events", "lastUpdateTime"}
    assert len(body["events"]) == 2
    assert set(body["events"][0].keys()) == {"id", "timestamp", "author"}


def test_filters_partial_false_default_and_authors():
    app = make_app(sample_session())
    client = TestClient(app)
    r = client.get(
        "/apps/app/users/u/sessions/s1",
        params={
            "authors": "planner_agent",
            "include_event_fields": "id,author",
        },
    )
    assert r.status_code == 200
    evs = r.json()["events"]
    # partial=True events should be excluded by default
    assert all(e["author"] == "planner_agent" for e in evs)
    assert all("id" in e for e in evs)


def test_windowing_after_id_and_sort_desc():
    app = make_app(sample_session())
    client = TestClient(app)
    r = client.get(
        "/apps/app/users/u/sessions/s1",
        params={
            "events_after_id": "e1",
            "events_sort": "desc",
            "include_event_fields": "id",
        },
    )
    body = r.json()
    ids = [e["id"] for e in body["events"]]
    # After e1 → e2,e3 then sort desc → e3,e2; partial e3 excluded by default
    assert ids == ["e2"]


def test_parts_and_actions_projection_and_drop_empty():
    payload = sample_session()
    app = make_app(payload)
    client = TestClient(app)
    r = client.get(
        "/apps/app/users/u/sessions/s1",
        params={
            "include_event_fields": "id,content,actions",
            "include_part_types": "functionCall",
            "include_part_fields": "functionCall",
            "include_action_fields": "stateDelta",
            "drop_empty": "true",
        },
    )
    evs = r.json()["events"]
    # e1 becomes empty (text part dropped), e2 remains with functionCall, e3 partial dropped
    assert len(evs) == 1 and evs[0]["id"] == "e2"
    parts = evs[0]["content"]["parts"]
    assert parts and "functionCall" in parts[0] and "text" not in parts[0]
    assert "stateDelta" in evs[0]["actions"]

