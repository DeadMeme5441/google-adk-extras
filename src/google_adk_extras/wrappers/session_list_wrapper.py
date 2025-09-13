from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


SESSION_LIST_PATH_RE = re.compile(r"^/apps/[^/]+/users/[^/]+/sessions$")


def _parse_bool(val: Optional[str], default: bool) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "t", "yes", "y", "on")


def _parse_list(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [p.strip() for p in val.split(",") if p.strip()]


def _safe_float(val: Optional[str]) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except Exception:
        return None


VALID_TOP_FIELDS = {"id", "appName", "userId", "state", "events", "lastUpdateTime"}


def _transform_sessions(payload: List[Dict[str, Any]], query: Dict[str, str]) -> List[Dict[str, Any]]:
    sessions = payload

    # Filters
    after_ts = _safe_float(query.get("updated_after_ts"))
    before_ts = _safe_float(query.get("updated_before_ts"))
    id_prefix = query.get("id_prefix") or ""
    ids = set(_parse_list(query.get("ids")))

    if after_ts is not None:
        sessions = [s for s in sessions if float(s.get("lastUpdateTime", 0.0)) >= after_ts]
    if before_ts is not None:
        sessions = [s for s in sessions if float(s.get("lastUpdateTime", 0.0)) <= before_ts]
    if id_prefix:
        sessions = [s for s in sessions if str(s.get("id", "")).startswith(id_prefix)]
    if ids:
        sessions = [s for s in sessions if str(s.get("id")) in ids]

    # Sort
    sort = (query.get("sort") or "last_update_time_desc").lower()
    reverse = sort in ("last_update_time_desc", "lastupdatetime_desc", "desc")
    try:
        sessions.sort(key=lambda s: (float(s.get("lastUpdateTime", 0.0)), str(s.get("id", ""))), reverse=reverse)
    except Exception:
        pass

    # Limit
    try:
        limit = int(query.get("limit", "50"))
    except Exception:
        limit = 50
    if limit < 0:
        limit = 0
    if limit > 1000:
        limit = 1000
    sessions = sessions[:limit]

    # Projection
    fields = [f for f in _parse_list(query.get("fields")) if f in VALID_TOP_FIELDS]
    if fields:
        sessions = [{k: v for k, v in s.items() if k in fields} for s in sessions]

    return sessions


class SessionListWrapperMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "GET" and SESSION_LIST_PATH_RE.match(request.url.path):
            response = await call_next(request)
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
            if content_type != "application/json":
                return response
            body_chunks: List[bytes] = []
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body_chunks.append(chunk)
            raw = b"".join(body_chunks)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                return Response(content=raw, status_code=response.status_code, headers=dict(response.headers), media_type=content_type)

            if not isinstance(payload, list):
                return Response(content=raw, status_code=response.status_code, headers=dict(response.headers), media_type=content_type)

            try:
                q = dict(request.query_params)
                transformed = _transform_sessions(payload, q)
                new_body = json.dumps(transformed, separators=(",", ":")).encode("utf-8")
            except Exception:
                new_body = raw

            headers = dict(response.headers)
            headers["content-length"] = str(len(new_body))
            return Response(content=new_body, status_code=response.status_code, headers=headers, media_type=content_type)

        return await call_next(request)

