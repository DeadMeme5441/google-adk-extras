# FastAPI Integration

Use `get_enhanced_fast_api_app` indirectly via `AdkBuilder.build_fastapi_app()`.

Key points
- Accepts your provided `credential_service` (no forced in‑memory default).
- Honors ADK’s Dev UI when assets are present.
- Preserves ADK’s runner caching/cleanup semantics via `EnhancedAdkWebServer`.

Example
```python
app = (
  AdkBuilder()
  .with_agents_dir("./agents")
  .with_session_service("sqlite:///./sessions.db")
  .with_artifact_service("local://./artifacts")
  .with_memory_service("yaml://./memory")
  .build_fastapi_app()
)
```

Dev UI
- Set `with_web_ui(True)`; if ADK’s web assets are available, the UI is served.
- Use `with_agent_reload(True)` for filesystem agent hot‑reload.
