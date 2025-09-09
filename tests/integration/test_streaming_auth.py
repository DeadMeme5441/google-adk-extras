import asyncio
import time
from fastapi.testclient import TestClient

from google.genai import types
from google.adk.events.event import Event

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.auth import AuthConfig, JwtValidatorConfig
from google_adk_extras.auth.jwt_utils import encode_jwt, now_ts


class _FakeRunner:
    async def run_async(self, *, user_id, session_id, new_message, state_delta=None, run_config=None):
        # Emit two quick events to keep things moving
        yield Event(author="agent", content=types.Content(parts=[types.Part(text="ok-1")]))
        yield Event(author="agent", content=types.Content(parts=[types.Part(text="ok-2")]))


def _build_app_with_auth(secret: str):
    loader = CustomAgentLoader()
    cfg = AuthConfig(
        enabled=True,
        jwt_validator=JwtValidatorConfig(issuer="issuer", audience="aud", hs256_secret=secret),
    )
    app = get_enhanced_fast_api_app(agent_loader=loader, web=False, enable_streaming=True, auth_config=cfg)
    # Stub runner
    app.state.streaming_controller._get_runner_async = lambda app_name: asyncio.sleep(0, result=_FakeRunner())
    return app


def _bearer(sub: str, secret: str) -> dict:
    now = now_ts()
    token = encode_jwt(
        {
            "iss": "issuer",
            "aud": "aud",
            "sub": sub,
            "iat": now,
            "nbf": now,
            "exp": now + 600,
        },
        algorithm="HS256",
        key=secret,
    )
    return {"Authorization": f"Bearer {token}"}


def test_sse_requires_auth_and_ownership():
    secret = "topsecret"
    app = _build_app_with_auth(secret)
    client = TestClient(app)
    ch = "ch1"
    # 401 without auth
    r = client.get(f"/stream/events/{ch}?appName=demo&userId=u1", timeout=2)
    assert r.status_code == 401

    # 403 when subject mismatch
    headers = _bearer("not_u1", secret)
    r = client.get(f"/stream/events/{ch}?appName=demo&userId=u1", headers=headers, timeout=2)
    assert r.status_code == 403

    # We do not open a stream here to avoid blocking CI; auth success is implicitly
    # covered by the POST /stream/send path when a channel exists (404 vs 401 tested below).


def test_stream_send_requires_auth_and_channel_exists():
    secret = "topsecret"
    app = _build_app_with_auth(secret)
    client = TestClient(app)
    ch = "ch2"
    # 401 without auth
    r = client.post(f"/stream/send/{ch}", json={})
    assert r.status_code == 401

    # 404 with auth if channel not opened yet
    headers = _bearer("u1", secret)
    r = client.post(f"/stream/send/{ch}", headers=headers, json={"app_name": "demo", "user_id": "u1", "session_id": "s-1", "new_message": {"parts": [{"text": "hi"}]}})
    assert r.status_code == 404
