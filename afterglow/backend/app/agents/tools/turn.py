"""Shared helper: bump the agent's turn counter at the start of every tool.

Every tool wrapper (memory, transcript, control, action) calls `bump_turn`
as its first instruction. The counter is monotonically increasing across
the agent loop, so an `action_exec` audit row written by
`action_executor.execute_single_action(agent_turn=...)` can be joined to
its corresponding `agent_turn` audit row deterministically.
"""
from __future__ import annotations

from typing import Any


def bump_turn(tool_context: Any) -> int:
    """Increment and return the per-agent-loop turn counter.

    Safe on a missing or stateless `tool_context` (returns 0). Pattern:

        turn = bump_turn(tool_context)
    """
    if tool_context is None or not hasattr(tool_context, "state"):
        return 0
    prev = tool_context.state.get("turn_counter") or 0
    turn = int(prev) + 1
    tool_context.state["turn_counter"] = turn
    return turn
