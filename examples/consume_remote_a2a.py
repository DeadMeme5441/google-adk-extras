"""Register a RemoteA2aAgent client proxy by card URL.

Requires: google-adk[a2a]

Run: uvicorn examples.consume_remote_a2a:app --reload
"""

from google_adk_extras import AdkBuilder

try:
    from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
    from google.adk.agents import Agent
except Exception:  # pragma: no cover - example only
    AGENT_CARD_WELL_KNOWN_PATH = "/.well-known/agent.json"  # type: ignore
    Agent = None  # type: ignore


def build_app():
    if Agent is None:
        raise RuntimeError("google.adk[a2a] is required to run this example")

    root = Agent(
        model="gemini-2.0-flash",
        name="root",
        instruction="Delegate prime checks to prime_agent.",
    )

    card_url = f"http://localhost:8001/a2a/prime{AGENT_CARD_WELL_KNOWN_PATH}"

    app = (
        AdkBuilder()
        .with_remote_a2a_agent("prime_agent", card_url, description="Prime checker")
        .with_agent_instance("root", root)
        .build_fastapi_app()
    )
    return app


app = build_app()

