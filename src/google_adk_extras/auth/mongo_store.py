from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
import base64
import hashlib
import secrets
import uuid

try:  # optional backend
    from pymongo import MongoClient
    from pymongo.collection import Collection
except Exception as e:  # pragma: no cover
    raise ImportError(
        "PyMongo is required for the auth Mongo store. Install with: pip install pymongo"
    ) from e


def _pbkdf2(password: str, salt: bytes | str, iterations: int = 120_000) -> str:
    if isinstance(salt, str):
        salt = salt.encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return base64.b64encode(dk).decode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"pbkdf2_sha256${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return secrets.compare_digest(password, stored)
        return secrets.compare_digest(_pbkdf2(password, salt), digest)
    except Exception:
        return False


class AuthStore:
    """Mongo-backed AuthStore with API compatible to the SQL variant."""

    def __init__(self, database_url: str, db_name: str = "adk_auth"):
        try:
            self.client = MongoClient(database_url, tz_aware=True)
        except TypeError:
            self.client = MongoClient(database_url)
        self.db = self.client[db_name]
        self.users: Collection = self.db["users"]
        self.refresh_tokens: Collection = self.db["refresh_tokens"]
        self.api_keys: Collection = self.db["api_keys"]
        # indexes
        try:  # best-effort
            self.users.create_index("username", unique=True)
            self.refresh_tokens.create_index("jti", unique=True)
            self.refresh_tokens.create_index([("user_id", 1)])
            self.refresh_tokens.create_index("expires_at")
            self.api_keys.create_index("id", unique=True)
            self.api_keys.create_index("revoked_at")
        except Exception:
            pass

    # ---- Users ----
    def create_user(self, username: str, password: str, user_id: Optional[str] = None) -> str:
        uid = user_id or str(uuid.uuid4())
        doc = {
            "_id": uid,
            "id": uid,
            "username": username,
            "password_hash": hash_password(password),
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
        }
        self.users.insert_one(doc)
        return uid

    def authenticate_basic(self, username: str, password: str) -> Optional[str]:
        u = self.users.find_one({"username": username})
        if not u or bool(u.get("disabled")):
            return None
        if verify_password(password, u.get("password_hash", "")):
            return str(u.get("id"))
        return None

    # ---- Refresh tokens ----
    def issue_refresh(self, user_id: str, ttl_seconds: int, fingerprint: Optional[str] = None) -> str:
        jti = str(uuid.uuid4())
        self.refresh_tokens.insert_one(
            {
                "jti": jti,
                "user_id": user_id,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
                "fingerprint": fingerprint,
                "revoked_at": None,
                "created_at": datetime.now(timezone.utc),
            }
        )
        return jti

    def verify_refresh(self, jti: str, user_id: str, fingerprint: Optional[str] = None) -> bool:
        try:
            rt = self.refresh_tokens.find_one({"jti": jti, "user_id": user_id})
            if not rt or rt.get("revoked_at") is not None:
                return False
            exp = rt.get("expires_at")
            if not exp:
                return False
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp)
                except Exception:
                    return False
            if getattr(exp, "tzinfo", None) is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= datetime.now(timezone.utc):
                return False
            if fingerprint and rt.get("fingerprint") and rt.get("fingerprint") != fingerprint:
                return False
            return True
        except Exception:
            return False

    def revoke_refresh(self, jti: str) -> None:
        self.refresh_tokens.update_one({"jti": jti}, {"$set": {"revoked_at": datetime.now(timezone.utc)}})

    # ---- API Keys ----
    def _hash_api_key(self, key: str) -> str:
        salt = secrets.token_hex(16)
        return f"api_pbkdf2_sha256${salt}${_pbkdf2(key, salt)}"

    def _verify_api_key(self, key: str, stored: str) -> bool:
        try:
            algo, salt, digest = stored.split("$", 3)
            if algo != "api_pbkdf2_sha256":
                return secrets.compare_digest(key, stored)
            return secrets.compare_digest(_pbkdf2(key, salt), digest)
        except Exception:
            return False

    def create_api_key(self, user_id: Optional[str] = None, name: Optional[str] = None) -> tuple[str, str]:
        key_plain = secrets.token_urlsafe(32)
        key_id = str(uuid.uuid4())
        self.api_keys.insert_one(
            {
                "id": key_id,
                "user_id": user_id,
                "name": name,
                "key_hash": self._hash_api_key(key_plain),
                "created_at": datetime.now(timezone.utc),
                "revoked_at": None,
            }
        )
        return key_id, key_plain

    def list_api_keys(self):
        rows = list(self.api_keys.find({}))
        out = []
        for r in rows:
            created = r.get("created_at")
            if isinstance(created, datetime) and getattr(created, "tzinfo", None) is None:
                created = created.replace(tzinfo=timezone.utc)
            out.append(
                {
                    "id": r.get("id"),
                    "user_id": r.get("user_id"),
                    "name": r.get("name"),
                    "created_at": created.isoformat() if isinstance(created, datetime) else None,
                    "revoked": r.get("revoked_at") is not None,
                }
            )
        return out

    def revoke_api_key(self, key_id: str) -> None:
        self.api_keys.update_one({"id": key_id}, {"$set": {"revoked_at": datetime.now(timezone.utc)}})

    def verify_api_key(self, key: str) -> bool:
        rows = list(self.api_keys.find({"revoked_at": None}))
        for r in rows:
            if self._verify_api_key(key, r.get("key_hash", "")):
                return True
        return False

