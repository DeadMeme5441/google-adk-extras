"""Streaming (SSE + WebSocket) example using AdkBuilder.

Run:
  uvicorn examples.streaming_sse_ws:app --reload

This example enables the optional streaming layer and exposes routes under
`/stream`:
- GET  /stream/events/{channelId}?appName=&userId=&sessionId= (SSE)
- POST /stream/send/{channelId}  (body = RunAgentRequest JSON)
- WS   /stream/ws/{channelId}?appName=&userId=&sessionId=

Notes:
- On open, the server emits a channel-bound control message containing the
  bound sessionId so the client can populate RunAgentRequest.
"""

from google_adk_extras import AdkBuilder


app = (
    AdkBuilder()
    # Use either on-disk agents or programmatic agents. For streaming layer,
    # the agent loader is optional if you stub the runner in tests; in real apps
    # provide your agents via one of these methods:
    # .with_agents_dir("./agents")

    # Enable streaming layer with defaults
    .with_web_ui(False)
    .build_fastapi_app(enable_streaming=True)
)

