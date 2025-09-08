"""Streaming support (SSE/WebSocket) for google-adk-extras.

This package provides an optional, persistent bi-directional streaming layer
with strict ADK type parity by default. It complements ADK's built-in
`/run`, `/run_sse`, and `/run_live` endpoints by offering per-channel
subscription and send semantics for chat-style UIs.
"""

from .streaming_controller import StreamingConfig, StreamingController

__all__ = ["StreamingConfig", "StreamingController"]

