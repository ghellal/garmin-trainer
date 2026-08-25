"""
Training coach agent: plans training using the Claude Agent SDK and the
``garmin-mcp`` server for read-only access to the local Garmin SQLite database.

The agent calls semantic MCP tools (``get_training_load``, ``get_sleep``, etc.)
rather than running raw SQL. It streams the response to stdout.
"""

import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from dotenv import load_dotenv


load_dotenv()

# Force subscription auth (Claude Pro/Max via `claude login`) over API key billing.
# If ANTHROPIC_API_KEY leaks in from the shell or .env, Claude Code would prefer it.
os.environ.pop("ANTHROPIC_API_KEY", None)


def _resolve_garmin_mcp() -> str:
    """
    Locate the ``garmin-mcp`` executable.

    Falls back to the current interpreter's bin directory so the script works
    even when the venv is not activated (e.g., ``.venv/bin/python script.py``).
    """
    found = shutil.which("garmin-mcp")
    if found:
        return found
    candidate = Path(sys.executable).parent / "garmin-mcp"
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError(
        "garmin-mcp not found on PATH or alongside the Python interpreter. "
        "Install it with: pip install -e ../garmin-data"
    )


MODEL = "claude-opus-4-7"

GARMIN_TOOLS = [
    "list_users",
    "get_user_profile",
    "get_recent_activities",
    "get_activity_details",
    "get_training_load",
    "get_training_readiness",
    "get_sleep",
    "get_hrv_trend",
    "get_vo2_max_trend",
    "get_personal_records",
    "get_race_predictions",
]

COACHING_PERSONA = """You are an evidence-based endurance coach with deep
expertise in periodization, recovery science, and Garmin health metrics
(VO2 max, training load, training readiness, body battery, HRV, sleep
architecture).

You access the user's data exclusively through the `garmin` MCP server's tools.
Never fabricate numbers — always pull them with a tool call.

Suggested workflow:
1. Call `get_user_profile` to anchor on age, VO2max, and lactate threshold HR.
2. Pull 30-42 days of `get_training_load` and `get_training_readiness` to assess
   ACWR, training status, and recovery state.
3. Pull `get_sleep` and `get_hrv_trend` for recovery markers.
4. Pull `get_recent_activities` to see what the user has actually been doing.
5. If a session looks important or anomalous, drill in with `get_activity_details`.
6. Optionally check `get_vo2_max_trend` and `get_race_predictions` for fitness
   direction.

When you respond:
- Identify trends — improving fitness, accumulating fatigue, sleep debt, HRV
  depression, ACWR > 1.5, training-load imbalance.
- Propose a concrete 7-day plan with specific session types, durations, target
  HR zones or RPE, and rest days. Reference the user's actual numbers.
- Flag concerns — sudden HRV drops, chronic sleep deprivation, signs of
  non-functional overreaching.

Be specific with numbers. Cite the data you draw from. Never recommend training
through illness or severe fatigue. If the data is sparse, say so and ask what's
missing rather than fabricating recommendations."""


async def coach(question: str) -> None:
    """
    Stream a coaching response answering ``question`` using Garmin MCP tools.
    """
    db_path = os.getenv("GARMIN_DB_PATH", "")
    if not db_path or not Path(db_path).expanduser().exists():
        raise FileNotFoundError(
            f"Garmin DB not found at {db_path!r}. Set GARMIN_DB_PATH in .env."
        )

    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=COACHING_PERSONA,
        mcp_servers={
            "garmin": {
                "type": "stdio",
                "command": _resolve_garmin_mcp(),
                "env": {"GARMIN_DB_PATH": db_path},
            }
        },
        allowed_tools=[f"mcp__garmin__{t}" for t in GARMIN_TOOLS],
    )

    final: ResultMessage | None = None
    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
                elif isinstance(block, ToolUseBlock):
                    print(f"\n[tool: {block.name}]", file=sys.stderr, flush=True)
        elif isinstance(message, ResultMessage):
            final = message

    print()
    if final is not None:
        usage = final.usage or {}
        print(
            f"\n[turns: {final.num_turns}, "
            f"input: {usage.get('input_tokens', 0)}, "
            f"output: {usage.get('output_tokens', 0)}, "
            f"cache_read: {usage.get('cache_read_input_tokens', 0)}]"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Garmin training coach agent.")
    parser.add_argument(
        "--question",
        default="Plan my next 7 days.",
        help="What to ask the coach",
    )
    args = parser.parse_args()
    asyncio.run(coach(question=args.question))


if __name__ == "__main__":
    main()
