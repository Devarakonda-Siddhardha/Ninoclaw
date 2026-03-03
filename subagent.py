"""
Sub-agent runner for Ninoclaw.

Allows the main AI to delegate tasks to specialized agents that can
reason across multiple steps and use tools autonomously.
"""
import json
from ai import chat

# Tools sub-agents are allowed to use (read-only / safe)
_SAFE_TOOL_NAMES = {
    "web_search", "wikipedia_search", "calculate",
    "convert_currency", "get_weather", "get_news", "get_system_info",
}

_AGENT_PROMPTS = {
    "researcher": (
        "You are a focused research agent. Your job is to deeply research the given task "
        "using web_search and wikipedia_search. Make multiple searches if needed, then "
        "synthesize everything into a comprehensive, well-structured answer. "
        "Always cite where information came from."
    ),
    "coder": (
        "You are a coding assistant agent. Write clean, working code for the task. "
        "Think step by step, explain your approach, and provide complete runnable code. "
        "Use calculate if you need to verify logic."
    ),
    "analyst": (
        "You are a data analysis agent. Break down the task analytically, "
        "use calculate for any math, use web_search for data you don't know. "
        "Present findings clearly with numbers and reasoning."
    ),
    "planner": (
        "You are a planning agent. Break the task into clear actionable steps. "
        "Research any unknowns with web_search. Output a structured, numbered plan "
        "with details for each step."
    ),
    "autonomous": (
        "You are an autonomous general-purpose agent. Use whatever tools you need "
        "to fully complete the given task. Think step by step. Keep working until "
        "you have a complete, high-quality answer."
    ),
}


async def run_subagent(agent_type: str, task: str, user_id: int, task_manager) -> str:
    """
    Run a sub-agent that can autonomously use tools to complete a task.

    Args:
        agent_type: One of researcher, coder, analyst, planner, autonomous
        task: The task description
        user_id: Forwarded for tool execution context
        task_manager: Forwarded for tool execution context

    Returns:
        Final answer string from the sub-agent
    """
    from tools import execute_tool, _BUILTIN_TOOLS
    import skill_manager as sm

    system_prompt = _AGENT_PROMPTS.get(agent_type, _AGENT_PROMPTS["autonomous"])
    system_prompt += (
        "\n\nYou are running as a sub-agent. Complete the task fully before finishing. "
        "Do not ask clarifying questions — make reasonable assumptions and proceed."
    )

    # Build allowed tool list
    all_tools = _BUILTIN_TOOLS + sm.get_tools()
    safe_tools = [
        t for t in all_tools
        if t["function"]["name"] in _SAFE_TOOL_NAMES
    ]

    history = []
    max_iterations = 6

    for iteration in range(max_iterations):
        response = chat(
            message=task if iteration == 0 else "Continue.",
            system_prompt=system_prompt,
            history=history,
            tools=safe_tools if safe_tools else None,
        )

        # Pure text response — done
        if isinstance(response, str):
            return response

        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if not tool_calls:
            return content or "_(agent returned no output)_"

        # Add assistant turn to history
        history.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})

        # Execute each tool call
        tool_outputs = []
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            raw_args = tc.get("function", {}).get("arguments", "{}")
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            tc_id = tc.get("id", f"call_{iteration}")

            if name not in _SAFE_TOOL_NAMES:
                result = f"⛔ Tool '{name}' is not available to sub-agents."
            else:
                try:
                    result = await execute_tool(name, args, user_id, task_manager)
                except Exception as e:
                    result = f"Tool error: {e}"

            tool_outputs.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": str(result),
            })

        history.extend(tool_outputs)

        # If no more tool calls expected, do one final pass to get text answer
        if iteration == max_iterations - 2:
            history.append({
                "role": "user",
                "content": "Now provide your final comprehensive answer based on everything above."
            })

    return "_(sub-agent reached iteration limit without finishing)_"
