---
title: Troubleshooting & FAQ
---

# Troubleshooting & FAQ

Common issues

- Docs build: mkdocstrings import errors — ensure `mkdocs.yml` has `paths: [src]` and package installs in the docs workflow.
- OAuth errors: invalid redirect URI or scope mismatch — recheck provider console and app callback.
- DB errors: connection refused or auth failed — validate network routes, credentials, and driver extras installed.
- Tool timeouts: increase per‑type timeouts; add retries and circuit breaker; inspect `get_performance_metrics()`.
- A2A routes missing: ensure `a2a=True` and `agents_dir` contains valid `agent.json` files.

FAQ

- Q: Can I use only one service type? A: Yes, mix any backends per need.
- Q: Do I need registries? A: Optional; useful for dynamic systems and hot‑swaps.
- Q: Where is the “EnhancedAgents” layer? A: Not included; use ADK agents directly.
- Q: How do I pick backends? A: YAML/Local/SQLite for dev; Postgres/Redis/S3 for prod.
