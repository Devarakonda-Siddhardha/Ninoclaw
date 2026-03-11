import os

filepath = r'c:\Users\LENOVO\Ninoclaw\tools.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """def _tool_requires_owner(tool_name: str) -> bool:
    return tool_name in _OWNER_ONLY_TOOLS or tool_name in _OWNER_ONLY_SKILL_TOOLS"""

replacement1 = """def _tool_requires_owner(tool_name: str) -> bool:
    return tool_name in _OWNER_ONLY_TOOLS or tool_name in _OWNER_ONLY_SKILL_TOOLS

# ── Tools requiring Human-in-the-Loop Confirmation ────────────────────────────
_CONFIRMATION_REQUIRED_TOOLS = {
    "run_command", "expo_delete_app", "web_delete", "delete_skill", "create_integration"
}

def _tool_requires_confirmation(tool_name: str) -> bool:
    return tool_name in _CONFIRMATION_REQUIRED_TOOLS"""

target2 = """    # ── Enforce owner-only access at execution time ───────────────────────
    if _tool_requires_owner(tool_name):
        err = require_owner(user_id)
        if err:
            return err"""

replacement2 = """    # ── Enforce owner-only access at execution time ───────────────────────
    if _tool_requires_owner(tool_name):
        err = require_owner(user_id)
        if err:
            return err

    # ── Enforce Human-in-the-Loop Confirmation ────────────────────────────
    if _tool_requires_confirmation(tool_name) and str(arguments.get("_confirmed", "")).lower() != "true":
        # Remove the hidden flag if it was somehow passed but was false, though it shouldn't be.
        import json
        # Pack the pending call into a special JSON signal
        return f"[REQUIRES_CONFIRMATION] {json.dumps({'name': tool_name, 'arguments': arguments})}"
"""

if target1 in content and target2 in content:
    content = content.replace(target1, replacement1)
    content = content.replace(target2, replacement2)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Patched tools.py")
else:
    print("ERROR: Target strings not found in tools.py")
    if target1 not in content: print("Target 1 missing")
    if target2 not in content: print("Target 2 missing")
