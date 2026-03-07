"""
Ninoclaw skill — create_integration
Lets the AI write new skill files on-the-fly for any app or service.
"""
import ast
import os
import sys
import re
from pathlib import Path

# Allow importing from the parent (Ninoclaw root) directory
sys.path.insert(0, str(Path(__file__).parent.parent))
import skill_manager

SKILL_INFO = {
    "name": "create_integration",
    "description": "Create a new integration/skill for any app or service by writing Python code",
    "icon": "🔌",
    "version": "1.0",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_integration",
            "description": (
                "Write and install a new skill/integration for any app or service. "
                "Use when the user says 'add integration with X', 'connect to Y app', "
                "'build a skill for Z', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the app or service (e.g. 'trello', 'notion', 'twitter')",
                    },
                    "description": {
                        "type": "string",
                        "description": "What the integration should do",
                    },
                    "api_docs_hint": {
                        "type": "string",
                        "description": "Any API details the user provided (optional)",
                    },
                },
                "required": ["app_name", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_integrations",
            "description": "List all currently loaded skills/integrations with their tools",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_SYSTEM_PROMPT = (
    "You are an expert Python developer writing a Ninoclaw skill. "
    "A skill must have: SKILL_INFO dict, TOOLS list (OpenAI tool definitions), "
    "execute(tool_name, arguments) -> str function. "
    "Use only requests library for HTTP. Read API keys from os.getenv(). "
    "Return plain strings. Never raise exceptions - catch all errors and return error strings."
)


def _build_user_prompt(app_name: str, description: str, api_docs_hint: str) -> str:
    hint_part = f" {api_docs_hint}" if api_docs_hint else ""
    return (
        f"Write a complete Python skill file for {app_name} integration. "
        f"Description: {description}.{hint_part} "
        "Include 2-4 useful tools. "
        "Add clear comments about which env vars need to be set."
    )


def _extract_code(text: str) -> str:
    """Strip ```python ... ``` fences if present, otherwise return as-is."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (``` or ```python) and last line (```)
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        return "\n".join(inner)
    return text


def _validate_syntax(code: str):
    """Return None if valid, else the SyntaxError."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return e


def _safe_skill_name(app_name: str) -> str:
    """Normalize user-provided app name to a safe Python module name."""
    name = re.sub(r"[^a-z0-9_]", "_", app_name.lower().strip())
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        name = "integration"
    if not re.match(r"^[a-z]", name):
        name = f"skill_{name}"
    return name[:50]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _do_create_integration(app_name: str, description: str, api_docs_hint: str) -> str:
    try:
        import ai  # local import — avoids circular import at module load time
    except ImportError as e:
        return f"Error: could not import ai module: {e}"

    user_prompt = _build_user_prompt(app_name, description, api_docs_hint)

    # First attempt
    response = ai.chat(
        user_prompt,
        system_prompt=_SKILL_SYSTEM_PROMPT,
        force_smart=True,
    )
    code = _extract_code(response)
    syntax_err = _validate_syntax(code)

    # Retry once on syntax error
    if syntax_err:
        retry_prompt = (
            f"{user_prompt}\n\n"
            f"Your previous attempt had a syntax error: {syntax_err}. "
            "Please fix it and return only valid Python code."
        )
        response = ai.chat(
            retry_prompt,
            system_prompt=_SKILL_SYSTEM_PROMPT,
            force_smart=True,
        )
        code = _extract_code(response)
        syntax_err = _validate_syntax(code)
        if syntax_err:
            return f"Error: generated code has a syntax error after retry: {syntax_err}"

    from security import validate_skill_code

    # Full safety validation before writing executable code to disk.
    err = validate_skill_code(code)
    if err:
        return err

    # Save skill file
    filename = _safe_skill_name(app_name) + ".py"
    skill_path = Path(__file__).parent / filename
    try:
        skill_path.write_text(code, encoding="utf-8")
    except OSError as e:
        return f"Error saving skill file: {e}"

    # Hot-reload all skills so the new one is immediately available
    skill_manager.load_skills()

    # Extract tool names and env var hints from the generated code for the summary
    tool_names = []
    env_vars = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Collect os.getenv() calls to list required env vars
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "getenv"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                env_vars.append(str(node.args[0].value))
            # Collect tool function names from TOOLS list
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "TOOLS":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Dict):
                                    for k, v in zip(elt.keys, elt.values):
                                        if (
                                            isinstance(k, ast.Constant)
                                            and k.value == "function"
                                            and isinstance(v, ast.Dict)
                                        ):
                                            for fk, fv in zip(v.keys, v.values):
                                                if (
                                                    isinstance(fk, ast.Constant)
                                                    and fk.value == "name"
                                                    and isinstance(fv, ast.Constant)
                                                ):
                                                    tool_names.append(fv.value)
    except Exception:
        pass

    lines = [f"✅ Integration '{app_name}' created and loaded: {skill_path.name}"]
    if tool_names:
        lines.append(f"\nTools available: {', '.join(tool_names)}")
    if env_vars:
        unique_vars = list(dict.fromkeys(env_vars))  # deduplicate while preserving order
        lines.append(f"\nEnv vars to set in .env: {', '.join(unique_vars)}")
    lines.append("\nRestart the bot to persist changes across restarts.")
    return "\n".join(lines)


def _do_list_integrations() -> str:
    # skill_manager._skills: dict[str, module]
    skills = skill_manager._skills
    if not skills:
        return "No integrations/skills currently loaded."

    lines = ["🔌 Loaded integrations & skills:\n"]
    for name, mod in skills.items():
        info = getattr(mod, "SKILL_INFO", {})
        icon = info.get("icon", "🔧")
        display = info.get("name", name)
        desc = info.get("description", "")
        tools = getattr(mod, "TOOLS", [])
        tool_names = []
        for t in tools:
            fn = t.get("function", {}).get("name")
            if fn:
                tool_names.append(fn)
        tool_str = f"  tools: {', '.join(tool_names)}" if tool_names else ""
        lines.append(f"{icon} {display} — {desc}{tool_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def execute(tool_name: str, arguments: dict) -> str:
    if tool_name == "create_integration":
        app_name = arguments.get("app_name", "").strip()
        description = arguments.get("description", "").strip()
        api_docs_hint = arguments.get("api_docs_hint", "").strip()
        if not app_name or not description:
            return "Error: app_name and description are required."
        return _do_create_integration(app_name, description, api_docs_hint)

    if tool_name == "list_integrations":
        return _do_list_integrations()

    return f"Unknown tool: {tool_name}"
