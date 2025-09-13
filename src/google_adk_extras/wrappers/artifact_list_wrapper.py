from __future__ import annotations

import json
import re
from typing import List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


ARTIFACTS_LIST_PATH_RE = re.compile(r"^/apps/[^/]+/users/[^/]+/sessions/[^/]+/artifacts$")


def _parse_list(val: str | None) -> list[str]:
    if not val:
        return []
    return [p.strip() for p in val.split(",") if p.strip()]


class ArtifactListWrapperMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "GET" and ARTIFACTS_LIST_PATH_RE.match(request.url.path):
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

            names: list[str] = [str(x) for x in payload]

            # Filters
            q = request.query_params
            prefix = q.get("prefix") or ""
            contains = q.get("contains") or ""
            regex = q.get("regex") or ""
            include = set(_parse_list(q.get("names")))

            if prefix:
                names = [n for n in names if n.startswith(prefix)]
            if contains:
                names = [n for n in names if contains in n]
            if include:
                names = [n for n in names if n in include]
            if regex:
                try:
                    import re as _re
                    r = _re.compile(regex)
                    names = [n for n in names if r.search(n)]
                except Exception:
                    pass

            # Sort
            sort = (q.get("sort") or "name_asc").lower()
            reverse = sort in ("name_desc", "desc")
            names.sort(reverse=reverse)

            # Windowing by name cursor
            after_name = q.get("after_name")
            before_name = q.get("before_name")
            if after_name and after_name in names:
                idx = names.index(after_name)
                names = names[idx + 1 :]
            if before_name and before_name in names:
                idx = names.index(before_name)
                names = names[:idx]

            # Limit
            try:
                limit = int(q.get("limit", "100"))
            except Exception:
                limit = 100
            if limit < 0:
                limit = 0
            if limit > 1000:
                limit = 1000
            names = names[:limit]

            new_body = json.dumps(names, separators=(",", ":")).encode("utf-8")
            headers = dict(response.headers)
            headers["content-length"] = str(len(new_body))
            return Response(content=new_body, status_code=response.status_code, headers=headers, media_type=content_type)

        return await call_next(request)

