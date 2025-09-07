---
title: Security
---

# Security

Credentials

- Store secrets outside source control; prefer secret managers.
- Rotate OAuth2 client secrets; restrict redirect URIs.
- JWT: use strong secrets/keys, set issuer/audience/expiry.
- Scope tokens narrowly; avoid long‑lived refresh tokens where possible.

Environment

- Interpolation: be mindful when enabling Python expressions; limit sources.
- Principle of least privilege for DBs and object storage.
- Separate dev/test/prod credentials and datasets; audit access.

Network

- Use TLS everywhere; terminate at the load balancer or service mesh.
- Consider rate limiting and WAF for public endpoints.
- Log auth failures and suspicious access patterns; alert on anomalies.
