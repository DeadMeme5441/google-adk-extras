Examples

This folder contains small, runnable examples that mirror the documentation. They are intentionally minimal and designed to be copy–pasted into your app.

- fastapi_app.py — Build a FastAPI app with durable services and optional credentials.
- runner_basic.py — Build a Runner for programmatic use without FastAPI.
- custom_loader.py — Register programmatic agents with `CustomAgentLoader`.
- services/ — Focused snippets for sessions, artifacts, memory backends.
- credentials/ — Focused snippets for the credential services.

Prereqs
- Python 3.12+
- Install package and extras you plan to run (uv), e.g.:
  - `uv pip install google-adk-extras[sql,yaml,web]`
  - For Redis/Mongo/S3/JWT: add the matching extras (`redis`, `mongodb`, `s3`, `jwt`).
