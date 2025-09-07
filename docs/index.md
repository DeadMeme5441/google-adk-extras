# Google ADK Extras

Production-ready extensions for Google ADK (Agent Development Kit). This library adds durable service backends (sessions, artifacts, memory), practical credential services (OAuth2/JWT/Basic), and clean FastAPI wiring so you can run ADK agents with real storage and auth.

- Works with ADK’s Runner, agents, tools, callbacks, and Dev UI.
- Provides a fluent `AdkBuilder` to assemble a FastAPI app or a `Runner`.
- Ships drop-in implementations for durable services and credential flows.

What this is not: a fork of ADK. It builds on top of google-adk.

## Public API Surface
- `AdkBuilder`
- `get_enhanced_fast_api_app`
- `EnhancedAdkWebServer`
- `EnhancedRunner` (thin wrapper)
- `CustomAgentLoader` (programmatic agents)
- Services via subpackages: `sessions`, `artifacts`, `memory`, `credentials`

See Quickstarts for copy‑paste examples.
