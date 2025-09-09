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


def test_api_key_create_use_revoke(tmp_path):
    db = tmp_path / "auth.db"
    client = build_app("topsecret", f"sqlite:///{db}")

    # Register user and token to manage keys
    r = client.post("/auth/register", params={"username": "admin", "password": "pw"})
    assert r.status_code == 200, r.text
    user_id = r.json()["user_id"]
    r = client.post("/auth/token", params={"grant_type": "password", "username": "admin", "password": "pw"})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]
    authz = {"Authorization": f"Bearer {access}"}

    # Create API key
    r = client.post("/auth/api-keys", headers=authz, params={"user_id": user_id, "name": "test"})
    assert r.status_code == 200, r.text
    key_id = r.json()["id"]
    key_plain = r.json()["api_key"]
    assert key_plain and len(key_plain) > 10

    # Use API key to access protected route
    r = client.get("/list-apps", headers={"X-API-Key": key_plain})
    assert r.status_code == 200, r.text

    # Revoke and verify denial
    r = client.delete(f"/auth/api-keys/{key_id}", headers=authz)
    assert r.status_code == 200, r.text
    r = client.get("/list-apps", headers={"X-API-Key": key_plain})
    assert r.status_code == 401

