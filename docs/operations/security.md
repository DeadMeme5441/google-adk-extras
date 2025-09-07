---
title: Security
---

# Security

Credentials

- Store secrets outside source control; prefer secret managers.
- Rotate OAuth2 client secrets; restrict redirect URIs.
- JWT: use strong secrets/keys, set issuer/audience/expiry.

Environment

- Interpolation: be mindful when enabling Python expressions; limit sources.
- Principle of least privilege for DBs and object storage.

Network

- Use TLS everywhere; terminate at the load balancer or service mesh.
- Consider rate limiting and WAF for public endpoints.

