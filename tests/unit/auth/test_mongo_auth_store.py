import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

# Create a stub pymongo module so the store can import without real dependency
class _StubCollectionModule(types.ModuleType):
    class Collection:  # type: ignore
        pass


stub_pymongo = types.ModuleType("pymongo")
stub_pymongo.collection = _StubCollectionModule("pymongo.collection")
class _DummyClient:
    pass
stub_pymongo.MongoClient = _DummyClient  # satisfies import at module load
sys.modules.setdefault("pymongo", stub_pymongo)
sys.modules.setdefault("pymongo.collection", stub_pymongo.collection)

from google_adk_extras.auth.mongo_store import AuthStore


class FakeCursor(list):
    def sort(self, *args, **kwargs):
        return self


class FakeCollection:
    def __init__(self):
        self.docs = []

    def create_index(self, *args, **kwargs):
        return None

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def _match(self, doc, filt):
        for k, v in (filt or {}).items():
            if isinstance(v, dict) and "$in" in v:
                if doc.get(k) not in v["$in"]:
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def find_one(self, filt):
        for d in self.docs:
            if self._match(d, filt):
                return dict(d)
        return None

    def update_one(self, filt, update):
        for i, d in enumerate(self.docs):
            if self._match(d, filt):
                if "$set" in update:
                    self.docs[i].update(update["$set"])
                return types.SimpleNamespace(matched_count=1)
        return types.SimpleNamespace(matched_count=0)

    def find(self, filt=None):
        out = [dict(d) for d in self.docs if self._match(d, filt or {})]
        return FakeCursor(out)


class FakeDB:
    def __init__(self):
        self.cols = {}

    def __getitem__(self, name):
        self.cols.setdefault(name, FakeCollection())
        return self.cols[name]


class FakeMongoClient:
    def __init__(self, *args, **kwargs):
        self.dbs = {}

    def __getitem__(self, name):
        self.dbs.setdefault(name, FakeDB())
        return self.dbs[name]

    def close(self):
        pass


@patch("google_adk_extras.auth.mongo_store.MongoClient", FakeMongoClient)
class TestMongoAuthStore:
    def test_user_and_basic_auth(self):
        store = AuthStore("mongodb://fake", "testdb")
        uid = store.create_user("alice", "wonderland")
        assert uid
        assert store.authenticate_basic("alice", "wrong") is None
        assert store.authenticate_basic("alice", "wonderland") == uid

    def test_refresh_token_flow(self):
        store = AuthStore("mongodb://fake", "testdb")
        uid = store.create_user("bob", "builder")
        jti = store.issue_refresh(uid, ttl_seconds=60, fingerprint="fp")
        assert store.verify_refresh(jti, uid, fingerprint="fp") is True
        # Expire it by setting a past naive datetime
        rt = store.refresh_tokens.find_one({"jti": jti})
        assert rt
        past = datetime.utcnow() - timedelta(seconds=10)  # naive
        store.refresh_tokens.update_one({"jti": jti}, {"$set": {"expires_at": past}})
        assert store.verify_refresh(jti, uid, fingerprint="fp") is False
        # Re-issue and revoke
        jti2 = store.issue_refresh(uid, ttl_seconds=60)
        store.revoke_refresh(jti2)
        assert store.verify_refresh(jti2, uid) is False

    def test_api_keys(self):
        store = AuthStore("mongodb://fake", "testdb")
        key_id, key_plain = store.create_api_key(user_id="u1", name="dev")
        assert key_id and key_plain
        assert store.verify_api_key(key_plain) is True
        # listing
        keys = store.list_api_keys()
        assert any(k["id"] == key_id for k in keys)
        store.revoke_api_key(key_id)
        assert store.verify_api_key(key_plain) is False
