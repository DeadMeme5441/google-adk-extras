# Troubleshooting

Common issues and fixes.

## ImportError: optional dependency
If `import jwt` or database clients fail, install the matching extras:

```bash
uv pip install google-adk-extras[jwt]      # PyJWT
uv pip install google-adk-extras[sql]      # SQLAlchemy
uv pip install google-adk-extras[mongodb]  # PyMongo
uv pip install google-adk-extras[redis]    # redis
uv pip install google-adk-extras[s3]       # boto3
```

## Dev UI not showing
- Ensure ADK’s web assets are available; set `.with_web_ui(True)`.
- If assets are missing, the app still runs; only the UI is skipped.

## Agents not found
- Using folders: ensure `./agents/<app>/agent.json` exists.
- Using `CustomAgentLoader`: confirm `register_agent(name, instance)` and use that `name`.

## State or events not saved
- Check the selected session backend and connection string.
- For SQL, confirm the DB file is writable and the table was created.

## Cloud tracing
- Not supported in this package (OpenTelemetry removed). If needed, add tracing in your app.
