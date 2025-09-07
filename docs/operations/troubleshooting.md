---
title: Troubleshooting & FAQ
---

# Troubleshooting & FAQ

Common issues

- Can’t import modules in API docs: ensure `mkdocs.yml` has `paths: [src]` for mkdocstrings.
- Credential errors: check client IDs/secrets and redirect URIs; verify scopes.
- DB connection errors: validate connection strings and network access.
- Tool timeouts: increase per‑type timeouts; add retries and circuit breaker.

FAQ

- Q: Can I use only one service type? A: Yes, mix any backends per need.
- Q: Do I need registries? A: Optional; useful for dynamic systems.
- Q: Where is the “EnhancedAgents” layer? A: Not included; use ADK agents directly.

