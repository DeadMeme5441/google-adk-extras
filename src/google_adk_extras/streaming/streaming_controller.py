import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable

from fastapi import HTTPException
from pydantic import BaseModel

from google.adk.events.event import Event
from google.adk.runners import Runner


class StreamingConfig(BaseModel):
    enable_streaming: bool = False
    streaming_path_base: str = "/stream"
    strict_types: bool = True
    create_session_on_open: bool = True
    ttl_seconds: int = 900
    max_queue_size: int = 128
    max_channels_per_user: int = 20
    heartbeat_interval: Optional[float] = 20.0
    reuse_session_policy: str = "per_channel"  # "per_channel" or "external"


@dataclass
class _Subscriber:
    queue: "asyncio.Queue[str]"
    kind: str  # "sse" | "ws"


@dataclass
class _Channel:
    channel_id: str
    app_name: str
    user_id: str
    session_id: str
    in_q: "asyncio.Queue[Any]" = field(default_factory=asyncio.Queue)
    subscribers: list[_Subscriber] = field(default_factory=list)
    worker_task: Optional[asyncio.Task] = None
    created_at: float = field(default_factory=lambda: time.time())
    last_activity: float = field(default_factory=lambda: time.time())
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class StreamingController:
    """Manages streaming channels and workers.

    This controller binds a channel to (app_name, user_id, session_id) and
    runs a background worker per channel to execute streamed runs and push
    ADK Event JSON to all subscribers.
    """

    def __init__(
        self,
        *,
        config: StreamingConfig,
        get_runner_async: Callable[[str], Awaitable[Runner]],
        session_service,
    ) -> None:
        self._config = config
        self._get_runner_async = get_runner_async
        self._session_service = session_service
        self._channels: Dict[str, _Channel] = {}
        self._gc_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._gc_task is None:
            self._gc_task = asyncio.create_task(self._gc_loop())

    async def stop(self) -> None:
        if self._gc_task:
            self._gc_task.cancel()
            with asyncio.CancelledError:
                pass
            self._gc_task = None
        # Cancel workers
        for ch in list(self._channels.values()):
            if ch.worker_task and not ch.worker_task.done():
                ch.worker_task.cancel()
        self._channels.clear()

    def _ensure_user_limit(self, user_id: str) -> None:
        if self._config.max_channels_per_user <= 0:
            return
        count = sum(1 for c in self._channels.values() if c.user_id == user_id)
        if count >= self._config.max_channels_per_user:
            raise HTTPException(status_code=429, detail="Too many channels for this user")

    async def open_or_bind_channel(
        self,
        *,
        channel_id: str,
        app_name: str,
        user_id: str,
        session_id: Optional[str],
    ) -> _Channel:
        # Existing channel validation/match
        if channel_id in self._channels:
            ch = self._channels[channel_id]
            if ch.app_name != app_name or ch.user_id != user_id:
                raise HTTPException(status_code=409, detail="Channel binding conflict")
            if session_id and session_id != ch.session_id:
                raise HTTPException(status_code=409, detail="Channel already bound to different session")
            ch.last_activity = time.time()
            return ch

        # New channel
        self._ensure_user_limit(user_id)
        if not session_id:
            if not self._config.create_session_on_open:
                raise HTTPException(status_code=400, detail="sessionId required for this channel")
            # Create a fresh ADK session
            create = getattr(self._session_service, "create_session", None)
            if create is None:
                # Older ADK interfaces may expose sync variant
                create = getattr(self._session_service, "create_session_sync", None)
            if create is None:
                raise HTTPException(status_code=500, detail="Session service does not support create_session")
            if asyncio.iscoroutinefunction(create):
                session = await create(app_name=app_name, user_id=user_id)
            else:
                # Call sync and wrap
                session = create(app_name=app_name, user_id=user_id)
            session_id = session.id
        else:
            # Validate existing session
            session = await self._session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

        ch = _Channel(
            channel_id=channel_id,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            in_q=asyncio.Queue(),
        )
        self._channels[channel_id] = ch
        ch.worker_task = asyncio.create_task(self._worker(ch))
        return ch

    def subscribe(self, channel_id: str, kind: str) -> asyncio.Queue[str]:
        if channel_id not in self._channels:
            raise HTTPException(status_code=404, detail="Channel not found")
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=self._config.max_queue_size)
        self._channels[channel_id].subscribers.append(_Subscriber(queue=q, kind=kind))
        self._channels[channel_id].last_activity = time.time()
        return q

    def unsubscribe(self, channel_id: str, q: asyncio.Queue[str]) -> None:
        ch = self._channels.get(channel_id)
        if not ch:
            return
        ch.subscribers = [s for s in ch.subscribers if s.queue is not q]
        ch.last_activity = time.time()

    async def enqueue(self, channel_id: str, req: Any) -> None:
        ch = self._channels.get(channel_id)
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        # Validate binding
        if getattr(req, "app_name", None) != ch.app_name or getattr(req, "user_id", None) != ch.user_id or getattr(req, "session_id", None) != ch.session_id:
            raise HTTPException(status_code=409, detail="Request does not match channel binding")
        await ch.in_q.put(req)
        ch.last_activity = time.time()

    async def _worker(self, ch: _Channel) -> None:
        try:
            while True:
                req = await ch.in_q.get()
                ch.last_activity = time.time()
                try:
                    runner = await self._get_runner_async(ch.app_name)
                    # Stream events for this request
                    async with _aclosing(
                        runner.run_async(
                            user_id=ch.user_id,
                            session_id=ch.session_id,
                            new_message=req.new_message,
                            state_delta=getattr(req, "state_delta", None),
                            run_config=_maybe_run_config_streaming(True),
                        )
                    ) as agen:
                        async for event in agen:
                            await self._broadcast_event(ch, event)
                except Exception as e:  # pragma: no cover - safety
                    await self._broadcast_error(ch, str(e))
        except asyncio.CancelledError:  # worker shutdown
            return

    async def _broadcast_event(self, ch: _Channel, event: Event) -> None:
        payload = event.model_dump_json(exclude_none=True, by_alias=True)
        for sub in list(ch.subscribers):
            try:
                sub.queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop subscriber on backpressure
                ch.subscribers = [s for s in ch.subscribers if s is not sub]
        ch.last_activity = time.time()

    async def _broadcast_heartbeat(self, ch: _Channel) -> None:
        if self._config.heartbeat_interval is None:
            return
        payload = '{"event":"heartbeat"}'
        for sub in list(ch.subscribers):
            try:
                sub.queue.put_nowait(payload)
            except asyncio.QueueFull:
                ch.subscribers = [s for s in ch.subscribers if s is not sub]

    async def _broadcast_error(self, ch: _Channel, message: str) -> None:
        payload = '{"error": %s}' % _json_escape(message)
        for sub in list(ch.subscribers):
            try:
                sub.queue.put_nowait(payload)
            except asyncio.QueueFull:
                ch.subscribers = [s for s in ch.subscribers if s is not sub]

    async def _gc_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(min(10, max(1, int(self._config.ttl_seconds / 3))))
                now = time.time()
                for cid, ch in list(self._channels.items()):
                    idle = now - ch.last_activity
                    if idle >= self._config.ttl_seconds and not ch.subscribers and ch.in_q.empty():
                        if ch.worker_task and not ch.worker_task.done():
                            ch.worker_task.cancel()
                        self._channels.pop(cid, None)
        except asyncio.CancelledError:
            return


# Utilities (avoid importing optional internals at module import time)
def _maybe_run_config_streaming(enabled: bool):
    # Support multiple ADK versions by resolving RunConfig/StreamingMode from
    # either google.adk.runners or google.adk.agents.run_config
    try:
        from google.adk.runners import RunConfig  # type: ignore
    except Exception:  # pragma: no cover - version fallback
        from google.adk.agents.run_config import RunConfig  # type: ignore
    try:
        from google.adk.agents.run_config import StreamingMode  # type: ignore
    except Exception:  # pragma: no cover - defensive
        StreamingMode = type("StreamingMode", (), {"SSE": "sse", "NONE": None})  # minimal stub
    return RunConfig(streaming_mode=StreamingMode.SSE if enabled else StreamingMode.NONE)


class _aclosing:
    def __init__(self, agen):
        self._agen = agen
    async def __aenter__(self):
        return self._agen
    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self._agen.aclose()
        except Exception:
            pass


def _json_escape(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
