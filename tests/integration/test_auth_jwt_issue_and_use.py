from fastapi.testclient import TestClient

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.auth import AuthConfig, JwtIssuerConfig, JwtValidatorConfig


def build_app(secret: str, db_url: str):
    loader = CustomAgentLoader()
    issuer = JwtIssuerConfig(
        enabled=True,
        issuer="https://local-issuer",
        audience="adk-api",
        algorithm="HS256",
        hs256_secret=secret,
        database_url=db_url,
        access_ttl_seconds=600,
        refresh_ttl_seconds=3600,
    )
    validator = JwtValidatorConfig(
        issuer=issuer.issuer,
        audience=issuer.audience,
        hs256_secret=secret,
    )
    cfg = AuthConfig(enabled=True, jwt_issuer=issuer, jwt_validator=validator)
    app = get_enhanced_fast_api_app(
        agent_loader=loader,
        web=False,
        enable_streaming=False,
        auth_config=cfg,
    )
    return TestClient(app)


def test_issue_and_call_protected_route(tmp_path):
    db = tmp_path / "auth.db"
    client = build_app("topsecret", f"sqlite:///{db}")

    # Register user and obtain tokens
    r = client.post("/auth/register", params={"username": "alice", "password": "wonder"})
    assert r.status_code == 200, r.text
    user_id = r.json()["user_id"]

    r = client.post("/auth/token", params={"grant_type": "password", "username": "alice", "password": "wonder"})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]

    # List sessions for this user under some app (none exist, but should authorize)
    r = client.get(f"/apps/demo/users/{user_id}/sessions", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data == [] or data == {"sessions": []}
