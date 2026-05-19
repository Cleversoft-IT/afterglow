"""Tool callables for the agentic post-call pipeline.

Every tool factory in this package returns an async callable suitable for
`google.adk.Agent(tools=[...])`. Each callable, as its first action, bumps
`tool_context.state["turn_counter"]` so audit correlation between
`agent_turn` rows (written by the runner) and `action_exec` rows (written
by `action_executor.execute_single_action`) is deterministic.
"""
