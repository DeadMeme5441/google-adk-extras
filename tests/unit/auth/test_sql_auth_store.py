from datetime import datetime, timedelta, timezone

import pytest

from google_adk_extras.auth.sql_store import AuthStore


class TestSqlAuthStore:
    def test_refresh_verify_and_expiry(self):
        store = AuthStore("sqlite:///:memory:")
        uid = store.create_user("charlie", "chocolate")
        jti = store.issue_refresh(uid, ttl_seconds=1)
        assert store.verify_refresh(jti, uid) is True
        # After expiry
        import time
        time.sleep(1.1)
        assert store.verify_refresh(jti, uid) is False

    def test_api_key_flow(self):
        store = AuthStore("sqlite:///:memory:")
        kid, key = store.create_api_key(user_id="u1", name="dev")
        assert store.verify_api_key(key) is True
        store.revoke_api_key(kid)
        assert store.verify_api_key(key) is False

