"""Expose a programmatic agent over A2A without an agents_dir.

Requires: google-adk (and optionally google-adk[a2a] when consuming remotely).

Run: uvicorn examples.programmatic_a2a_expose:app --reload
"""

from google_adk_extras import AdkBuilder

try:
    from google.adk.agents import Agent
except Exception:  # pragma: no cover - example only
    Agent = None  # type: ignore


def build_app():
    if Agent is None:
        raise RuntimeError("google.adk is required to run this example")

    hello = Agent(
        model="gemini-2.0-flash",
        name="hello",
        instruction="You are helpful. Greet the user succinctly.",
    )

    app = (
        AdkBuilder()
        .with_agent_instance("hello", hello)
        .with_a2a_protocol(True)
        .enable_a2a_for_registered_agents()  # Exposes at /a2a/hello
        .build_fastapi_app()
    )
    return app


app = build_app()

