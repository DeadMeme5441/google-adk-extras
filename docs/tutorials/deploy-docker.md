---
title: Tutorial — Deploy with Docker
---

# Tutorial: Deploy with Docker

Containerize and deploy the FastAPI app.

Steps

1) Create a minimal `Dockerfile` using `uvicorn`.
2) Bake environment variables for DBs and credentials via secrets.
3) Use a multi-stage build or slim base images.
4) Run behind a reverse proxy (e.g., Cloud Run, ECS, K8s ingress).

Example Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . && pip install --no-cache-dir uvicorn
CMD ["uvicorn", "my_app:app", "--host", "0.0.0.0", "--port", "8080"]
```

Security & Perf

- Don’t bake secrets into images; use environment or secret managers.
- Enable health checks and readiness probes where possible.
