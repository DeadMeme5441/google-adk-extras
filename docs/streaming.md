# Streaming

The optional streaming layer adds a persistent, bi‑directional channel on top of
Google ADK’s existing `/run`, `/run_sse`, and `/run_live` primitives. It exposes
simple endpoints for a chat‑style UI while keeping strict ADK type parity.

- Uplink payload: the exact ADK `RunAgentRequest` (JSON)
- Downlink events: the exact ADK `Event` JSON
- Per‑channel binding to `(appName, userId, sessionId)`

## Enable

```python
from google_adk_extras import AdkBuilder

app = (
    AdkBuilder()
      .with_agents_dir("./agents")  # or programmatic loader/instances
      .build_fastapi_app(enable_streaming=True)
)
```

Optional config:

```python
from google_adk_extras.streaming import StreamingConfig

cfg = StreamingConfig(
    streaming_path_base="/stream",
    strict_types=True,
    create_session_on_open=True,  # create a new ADK session on first subscribe
    ttl_seconds=900,
    max_queue_size=128,
    max_channels_per_user=20,
    heartbeat_interval=20.0,
)

app = AdkBuilder().with_agents_dir("./agents").build_fastapi_app(
    enable_streaming=True,
    streaming_config=cfg,
)
```

## Endpoints (default base: `/stream`)

- `GET  /stream/events/{channelId}?appName=&userId=&sessionId=` — SSE downlink
  - If `sessionId` is omitted and `create_session_on_open=True`, a session is created.
  - First, a control message is sent: `event: channel-bound` with `data: {appName,userId,sessionId}`.
  - Subsequent `data: ...` lines contain raw ADK `Event` JSON.

- `POST /stream/send/{channelId}` — enqueue a single run on the bound channel
  - Body must be a strict ADK `RunAgentRequest` JSON whose `(appName,userId,sessionId)`
    match the channel binding.

- `WS   /stream/ws/{channelId}?appName=&userId=&sessionId=` — WebSocket bidi
  - On connect, a `{"event":"channel-bound",...}` JSON frame is sent with the final `sessionId`.
  - Client sends strict `RunAgentRequest` JSON frames to enqueue runs.
  - Server streams raw ADK `Event` JSON frames back.

## Minimal Client Examples

SSE (browser):

```html
<script>
const ch = crypto.randomUUID();
const src = new EventSource(`/stream/events/${ch}?appName=my_app&userId=u1`);
let sessionId;
src.addEventListener('channel-bound', (e) => {
  const info = JSON.parse(e.data);
  sessionId = info.sessionId;
  // Now send a RunAgentRequest
  fetch(`/stream/send/${ch}`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      appName: "my_app",
      userId: "u1",
      sessionId,
      streaming: true,
      newMessage: { parts: [{ text: "Hello!" }] }
    })
  });
});

src.onmessage = (e) => {
  const event = JSON.parse(e.data); // ADK Event JSON
  console.log('event', event);
};
</script>
```

WebSocket (browser):

```html
<script>
const ch = crypto.randomUUID();
const ws = new WebSocket(`ws://${location.host}/stream/ws/${ch}?appName=my_app&userId=u1`);
let sessionId;
ws.onmessage = (msg) => {
  const data = JSON.parse(msg.data);
  if (data.event === 'channel-bound') {
    sessionId = data.sessionId;
    ws.send(JSON.stringify({
      appName: 'my_app', userId: 'u1', sessionId, streaming: true,
      newMessage: { parts: [{ text: 'Hello!' }] }
    }));
  } else {
    console.log('event', data); // ADK Event JSON
  }
};
</script>
```

### Notes
- This layer is optional. The core ADK endpoints remain available.
- By default we preserve ADK wire types. If you need a convenience payload
  (non‑strict), you can add your own translator at your API boundary.

