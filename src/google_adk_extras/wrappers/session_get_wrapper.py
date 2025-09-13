from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


SESSION_GET_PATH_RE = re.compile(r"^/apps/[^/]+/users/[^/]+/sessions/[^/]+$")


def _parse_bool(val: Optional[str], default: bool) -> bool:
    if val is None:
        return default
    v = val.strip().lower()
    if v in ("1", "true", "t", "yes", "y", "on"):
        return True
    if v in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


def _parse_list(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [p.strip() for p in val.split(",") if p.strip()]


def _safe_float(val: Optional[str]) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        # Support RFC3339 by letting frontend pass epoch seconds; advanced parsing could be added later
        return float(val)
    except Exception:
        return None


ALLOWED_EVENT_FIELDS = {
    "content",
    "actions",
    "groundingMetadata",
    "usageMetadata",
    "inputTranscription",
    "outputTranscription",
    "liveSessionResumptionUpdate",
    "customMetadata",
    "longRunningToolIds",
    "finishReason",
    "errorCode",
    "errorMessage",
    "interrupted",
    "turnComplete",
    "id",
    "timestamp",
    "author",
    "invocationId",
    "branch",
}

ALLOWED_PART_TYPES = {
    "text",
    "functionCall",
    "functionResponse",
    "inlineData",
    "fileData",
    "executableCode",
    "codeExecutionResult",
    "videoMetadata",
    "thought",
    "thoughtSignature",
}

ALLOWED_ACTION_FIELDS = {
    "stateDelta",
    "artifactDelta",
    "requestedAuthConfigs",
    "skipSummarization",
    "transferToAgent",
    "escalate",
}


def _event_type_of_part(part: Dict[str, Any]) -> Optional[str]:
    for k in ALLOWED_PART_TYPES:
        if k in part:
            return k
    # Some parts may have a `type` field in future; ignore otherwise
    return None


def _project_part(part: Dict[str, Any], include_part_fields: List[str]) -> Dict[str, Any]:
    if not include_part_fields:
        return part
    out = {}
    for k in include_part_fields:
        if k in part:
            out[k] = part[k]
    return out


def _contains_artifacts_from_state(state_delta: Dict[str, Any]) -> bool:
    if not state_delta:
        return False
    for k in state_delta.keys():
        lk = k.lower()
        if "artifact" in lk or lk.endswith("artifacts") or lk == "artifacts_index":
            return True
    return False


def _is_error_event(e: Dict[str, Any]) -> bool:
    if e.get("errorCode") or e.get("errorMessage"):
        return True
    # Heuristic: functionResponse with an embedded error-like field
    content = e.get("content") or {}
    parts: List[Dict[str, Any]] = content.get("parts") or []
    for p in parts:
        fr = p.get("functionResponse")
        if isinstance(fr, dict):
            res = fr.get("response") or fr.get("result") or fr.get("data")
            if isinstance(res, dict):
                if any(k.lower() == "error" or "error" in k.lower() for k in res.keys()):
                    return True
            if isinstance(res, str) and "error" in res.lower():
                return True
    return False


def _drop_empty_event(e: Dict[str, Any]) -> bool:
    # Empty if no parts, no state/artifact deltas, and no useful metadata
    content = e.get("content") or {}
    parts = content.get("parts") or []
    if parts:
        return False
    actions = e.get("actions") or {}
    if (actions.get("stateDelta") or actions.get("artifactDelta")):
        return False
    # Useful metadata markers (exclude generic author/invocationId to allow compact views)
    for k in ("finishReason", "errorCode", "errorMessage", "turnComplete"):
        if e.get(k):
            return False
    return True


def _window_by_ids(events: List[Dict[str, Any]], after_id: Optional[str], before_id: Optional[str]) -> List[Dict[str, Any]]:
    start = 0
    end = len(events)
    if after_id:
        for i, ev in enumerate(events):
            if ev.get("id") == after_id:
                start = i + 1
                break
    if before_id:
        for i, ev in enumerate(events):
            if ev.get("id") == before_id:
                end = i
                break
    return events[start:end]


def _transform_session(session_obj: Dict[str, Any], query: Dict[str, str]) -> Dict[str, Any]:
    # --- Top-level projections ---
    requested_fields = _parse_list(query.get("fields"))
    # Normalize field names to output aliases
    valid_top = {"id", "appName", "userId", "state", "events", "lastUpdateTime"}
    if requested_fields:
        keep_top = [f for f in requested_fields if f in valid_top]
    else:
        keep_top = list(valid_top)

    # --- Event projections and filters ---
    include_event_fields = [f for f in _parse_list(query.get("include_event_fields")) if f in ALLOWED_EVENT_FIELDS]
    include_part_types = [t for t in _parse_list(query.get("include_part_types")) if t in ALLOWED_PART_TYPES]
    include_part_fields = _parse_list(query.get("include_part_fields"))
    include_action_fields = [f for f in _parse_list(query.get("include_action_fields")) if f in ALLOWED_ACTION_FIELDS]

    authors = set(_parse_list(query.get("authors")))
    branches = set(_parse_list(query.get("branches")))

    partial = _parse_bool(query.get("partial"), default=False)
    errors_only = _parse_bool(query.get("errors_only"), default=False)
    with_state_changes = _parse_bool(query.get("with_state_changes"), default=False)
    with_artifacts = _parse_bool(query.get("with_artifacts"), default=False)
    drop_empty = _parse_bool(query.get("drop_empty"), default=True)

    # Windowing
    events_limit = query.get("events_limit")
    try:
        events_limit_i = int(events_limit) if events_limit is not None else None
    except Exception:
        events_limit_i = None
    after_id = query.get("events_after_id")
    before_id = query.get("events_before_id")
    since_ts = _safe_float(query.get("events_since_ts"))
    until_ts = _safe_float(query.get("events_until_ts"))
    sort_dir = (query.get("events_sort") or "asc").lower()
    if sort_dir not in ("asc", "desc"):
        sort_dir = "asc"

    # Obtain events list
    events: List[Dict[str, Any]] = session_obj.get("events") or []

    # Base sort asc by timestamp
    try:
        events.sort(key=lambda e: float(e.get("timestamp", 0.0)))
    except Exception:
        pass

    # Timestamp window
    if since_ts is not None:
        events = [e for e in events if float(e.get("timestamp", 0.0)) >= since_ts]
    if until_ts is not None:
        events = [e for e in events if float(e.get("timestamp", 0.0)) <= until_ts]

    # Cursor window
    events = _window_by_ids(events, after_id, before_id)

    # Filters
    if not partial:
        events = [e for e in events if not e.get("partial")]
    if authors:
        events = [e for e in events if (e.get("author") in authors)]
    if branches:
        events = [e for e in events if (e.get("branch") in branches)]
    if errors_only:
        events = [e for e in events if _is_error_event(e)]
    if with_state_changes:
        events = [e for e in events if (e.get("actions") or {}).get("stateDelta")]
    if with_artifacts:
        tmp = []
        for e in events:
            actions = e.get("actions") or {}
            if actions.get("artifactDelta") or _contains_artifacts_from_state(actions.get("stateDelta") or {}):
                tmp.append(e)
        events = tmp

    # Part filtering before drop_empty
    if include_part_types or include_part_fields:
        for e in events:
            content = e.get("content")
            if not isinstance(content, dict):
                continue
            parts = content.get("parts")
            if not isinstance(parts, list):
                continue
            new_parts: List[Dict[str, Any]] = []
            for p in parts:
                if not isinstance(p, dict):
                    continue
                ptype = _event_type_of_part(p)
                if include_part_types and ptype not in include_part_types:
                    continue
                new_parts.append(_project_part(p, include_part_fields))
            content["parts"] = new_parts

    # Optional heavy subtrees
    if not _parse_bool(query.get("include_usage"), default=True):
        for e in events:
            e.pop("usageMetadata", None)
    if not _parse_bool(query.get("include_grounding"), default=True):
        for e in events:
            e.pop("groundingMetadata", None)
    if not _parse_bool(query.get("include_transcriptions"), default=True):
        for e in events:
            e.pop("inputTranscription", None)
            e.pop("outputTranscription", None)
    if not _parse_bool(query.get("include_requested_auth"), default=True):
        for e in events:
            acts = e.get("actions")
            if isinstance(acts, dict):
                acts.pop("requestedAuthConfigs", None)

    # Action projection
    if include_action_fields:
        for e in events:
            acts = e.get("actions")
            if isinstance(acts, dict):
                e["actions"] = {k: v for k, v in acts.items() if k in include_action_fields}

    # Drop empties after filtering
    if drop_empty:
        events = [e for e in events if not _drop_empty_event(e)]

    # Sort direction and limit
    if sort_dir == "desc":
        events.reverse()
    if events_limit_i is not None and events_limit_i >= 0:
        events = events[: events_limit_i]

    # Event projection keys
    if include_event_fields:
        events = [
            {k: v for k, v in e.items() if k in include_event_fields}
            for e in events
        ]

    # Build final top-level projection
    out: Dict[str, Any] = {}
    for k in keep_top:
        if k == "events":
            out["events"] = events
        else:
            if k in session_obj:
                out[k] = session_obj[k]
    return out


class SessionGetWrapperMiddleware(BaseHTTPMiddleware):
    """Wraps the GET session endpoint response and applies filters/projections.

    This does not change routes; it intercepts the response for
    GET /apps/{app}/users/{user}/sessions/{sessionId} and rewrites JSON.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "GET" and SESSION_GET_PATH_RE.match(request.url.path):
            response = await call_next(request)
            # Only process JSON responses
            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            if content_type != "application/json":
                return response
            # Buffer body
            body_chunks: List[bytes] = []
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body_chunks.append(chunk)
            raw = b"".join(body_chunks)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                return Response(content=raw, status_code=response.status_code, headers=dict(response.headers), media_type=content_type)

            # Transform
            try:
                # Starlette QueryParams is Mapping[str, str]; here we just use request.query_params
                q = dict(request.query_params)
                transformed = _transform_session(payload, q)
                new_body = json.dumps(transformed, separators=(",", ":")).encode("utf-8")
            except Exception:
                # On any failure, fall back to original body
                new_body = raw

            # Return new response
            headers = dict(response.headers)
            headers["content-length"] = str(len(new_body))
            return Response(content=new_body, status_code=response.status_code, headers=headers, media_type=content_type)

        return await call_next(request)
