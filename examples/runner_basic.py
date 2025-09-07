"""Basic Runner construction example.

Run this inside an async context or an asyncio REPL.
Requires (uv):
  uv pip install google-adk-extras[sql,yaml]
"""

import asyncio
from google_adk_extras import AdkBuilder


async def main():
    runner = (
        AdkBuilder()
        .with_agents_dir("./agents")
        .with_session_service("sqlite:///./sessions.db")
        .with_artifact_service("local://./artifacts")
        .with_memory_service("yaml://./memory")
        .build_runner("my_agent")
    )

    result = await runner.run("Hello there!")
    print(result.text if hasattr(result, "text") else result)


if __name__ == "__main__":
    asyncio.run(main())
