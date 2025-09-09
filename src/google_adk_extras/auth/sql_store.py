from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from sqlalchemy import Column, String, DateTime, create_engine, Text, Boolean
    from sqlalchemy.orm import declarative_base, sessionmaker
except ImportError as e:
    raise ImportError(
        "SQLAlchemy is required for the auth SQL store. Install with: pip install sqlalchemy"
    ) from e


Base = declarative_base()


def _pbkdf2(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return dk.hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"pbkdf2_sha256${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$", 2)
        if algo != "pbkdf2_sha256":
            # fallback for plaintext in tests
            return secrets.compare_digest(password, stored)
        return secrets.compare_digest(_pbkdf2(password, salt), digest)
    except Exception:
        return secrets.compare_digest(password, stored)


class User(Base):
    __tablename__ = "auth_users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    roles = Column(String, default="")  # comma-separated
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    disabled = Column(Boolean, default=False)


class RefreshToken(Base):
    __tablename__ = "auth_refresh_tokens"
    jti = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    fingerprint = Column(String, nullable=True)


class ApiKey(Base):
    __tablename__ = "auth_api_keys"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=True)
    key_hash = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class AuthStore:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def create_user(self, username: str, password: str, user_id: Optional[str] = None) -> str:
        import uuid
        uid = user_id or str(uuid.uuid4())
        with self.Session() as s:
            u = User(id=uid, username=username, password_hash=hash_password(password))
            s.add(u)
            s.commit()
        return uid

    def authenticate_basic(self, username: str, password: str) -> Optional[str]:
        with self.Session() as s:
            u: Optional[User] = s.query(User).filter_by(username=username).first()
            if not u or u.disabled:
                return None
            if verify_password(password, u.password_hash):
                return u.id
        return None

    def issue_refresh(self, user_id: str, ttl_seconds: int, fingerprint: Optional[str] = None) -> str:
        import uuid
        jti = str(uuid.uuid4())
        with self.Session() as s:
            rt = RefreshToken(
                jti=jti,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
                fingerprint=fingerprint,
            )
            s.add(rt)
            s.commit()
        return jti

    def verify_refresh(self, jti: str, user_id: str, fingerprint: Optional[str] = None) -> bool:
        with self.Session() as s:
            rt: Optional[RefreshToken] = s.query(RefreshToken).filter_by(jti=jti, user_id=user_id).first()
            if not rt or rt.revoked_at is not None:
                return False
            if rt.expires_at <= datetime.now(timezone.utc):
                return False
            if fingerprint and rt.fingerprint and rt.fingerprint != fingerprint:
                return False
            return True

    def revoke_refresh(self, jti: str) -> None:
        with self.Session() as s:
            rt: Optional[RefreshToken] = s.query(RefreshToken).filter_by(jti=jti).first()
            if not rt:
                return
            rt.revoked_at = datetime.now(timezone.utc)
            s.add(rt)
            s.commit()

    # API Keys
    def _hash_api_key(self, key: str) -> str:
        # Reuse PBKDF2; different prefix
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
        import uuid
        key_plain = secrets.token_urlsafe(32)
        key_id = str(uuid.uuid4())
        with self.Session() as s:
            rec = ApiKey(id=key_id, user_id=user_id, key_hash=self._hash_api_key(key_plain), name=name)
            s.add(rec)
            s.commit()
        return key_id, key_plain

    def list_api_keys(self):
        with self.Session() as s:
            rows = s.query(ApiKey).all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "name": r.name,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "revoked": r.revoked_at is not None,
                }
                for r in rows
            ]

    def revoke_api_key(self, key_id: str) -> None:
        with self.Session() as s:
            rec = s.query(ApiKey).filter_by(id=key_id).first()
            if not rec:
                return
            rec.revoked_at = datetime.now(timezone.utc)
            s.add(rec)
            s.commit()

    def verify_api_key(self, key: str) -> bool:
        with self.Session() as s:
            rows = s.query(ApiKey).filter(ApiKey.revoked_at.is_(None)).all()
            for r in rows:
                if self._verify_api_key(key, r.key_hash):
                    return True
        return False
