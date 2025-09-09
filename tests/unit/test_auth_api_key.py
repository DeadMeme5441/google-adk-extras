from fastapi.testclient import TestClient

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.auth import AuthConfig


def build_app_basic(user: str, pwd: str) -> TestClient:
    loader = CustomAgentLoader()
    app = get_enhanced_fast_api_app(
        agent_loader=loader,
        web=False,
        enable_streaming=False,
        auth_config=AuthConfig(enabled=True, basic_users={user: pwd})
    )
    return TestClient(app)


def test_list_apps_requires_basic():
    client = build_app_basic("a", "b")
    # Unauthorized
    r = client.get("/list-apps")
    assert r.status_code == 401
    # Authorized
    r = client.get("/list-apps", headers={"Authorization": "Basic YTpi"})
    assert r.status_code == 200
