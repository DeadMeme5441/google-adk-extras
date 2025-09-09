"""Example ADK server on 127.0.0.1:8003 with web UI enabled.

- Uses programmatic agent loader (no on-disk agents required to start).
- Web UI auto-mounts if your installed google-adk wheel ships fast_api/browser.
  You can override with WEB_ASSETS_DIR env var to point at an Angular dist.
"""

import os
from pathlib import Path
import uvicorn

from google_adk_extras.enhanced_fast_api import get_enhanced_fast_api_app
from google_adk_extras.custom_agent_loader import CustomAgentLoader


def build_app():
    loader = CustomAgentLoader()
    app = get_enhanced_fast_api_app(
        agent_loader=loader,
        web=False,
        enable_streaming=True,
    )
    return app


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")
