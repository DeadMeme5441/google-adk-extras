from fastapi.testclient import TestClient

from google_adk_extras.enhanced_fastapi import get_enhanced_fast_api_app
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.auth import AuthConfig, JwtValidatorConfig
from google_adk_extras.auth.jwt_utils import encode_jwt, now_ts


def _bearer(sub: str, secret: str) -> dict:
    now = now_ts()
    token = encode_jwt({"iss": "iss", "aud": "aud", "sub": sub, "iat": now, "nbf": now, "exp": now + 600}, algorithm="HS256", key=secret)
    return {"Authorization": f"Bearer {token}"}


def test_only_jwt_allowed_disables_api_key_and_basic():
    secret = "s"
    cfg = AuthConfig(
        enabled=True,
        jwt_validator=JwtValidatorConfig(issuer="iss", audience="aud", hs256_secret=secret),
        allow_bearer_jwt=True,
        allow_api_key=False,
        allow_basic=False,
    )
    app = get_enhanced_fast_api_app(agent_loader=CustomAgentLoader(), web=False, auth_config=cfg)
    c = TestClient(app)
    # No auth → 401
    assert c.get("/list-apps").status_code == 401
    # API key denied
    assert c.get("/list-apps", headers={"X-API-Key": "x"}).status_code == 401
    # Basic denied
    assert c.get("/list-apps", headers={"Authorization": "Basic YTpi"}).status_code == 401
    # JWT works
    assert c.get("/list-apps", headers=_bearer("u", secret)).status_code == 200


def test_api_key_header_only_disables_query_param():
    cfg = AuthConfig(
        enabled=True,
        api_keys=["k"],
        allow_api_key=True,
        allow_query_api_key=False,
        allow_bearer_jwt=False,
        allow_basic=False,
    )
    app = get_enhanced_fast_api_app(agent_loader=CustomAgentLoader(), web=False, auth_config=cfg)
    c = TestClient(app)
    # Query param should be denied
    assert c.get("/list-apps?api_key=k").status_code == 401
    # Header should work
    assert c.get("/list-apps", headers={"X-API-Key": "k"}).status_code == 200


def test_basic_only():
    cfg = AuthConfig(
        enabled=True,
        basic_users={"a": "b"},
        allow_basic=True,
        allow_api_key=False,
        allow_bearer_jwt=False,
    )
    app = get_enhanced_fast_api_app(agent_loader=CustomAgentLoader(), web=False, auth_config=cfg)
    c = TestClient(app)
    # Without creds → 401
    assert c.get("/list-apps").status_code == 401
    # Basic works
    assert c.get("/list-apps", headers={"Authorization": "Basic YTpi"}).status_code == 200
    # API key denied
    assert c.get("/list-apps", headers={"X-API-Key": "k"}).status_code == 401
    # JWT denied
    assert c.get("/list-apps", headers={"Authorization": "Bearer t"}).status_code == 401

