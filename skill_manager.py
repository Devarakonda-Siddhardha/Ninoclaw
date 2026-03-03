"""
Ninoclaw Skill Manager — auto-discovers and loads skills from the skills/ folder.

Each skill must have:
  - SKILL_INFO dict  (name, description, icon, version)
  - TOOLS list       (OpenAI tool definitions)
  - execute(tool_name, arguments) -> str
"""
import os, sys, importlib
from pathlib import Path
from dotenv import dotenv_values

SKILLS_DIR = Path(__file__).parent / "skills"
ENV_FILE   = Path(__file__).parent / ".env"

_skills = {}   # skill_name -> module

def _disabled_skills():
    env = dotenv_values(str(ENV_FILE))
    raw = env.get("DISABLED_SKILLS", "")
    return {s.strip() for s in raw.split(",") if s.strip()}

def load_skills():
    """Scan skills/ folder and import every valid skill module."""
    global _skills
    _skills = {}
    if not SKILLS_DIR.exists():
        return
    disabled = _disabled_skills()
    sys.path.insert(0, str(Path(__file__).parent))
    for f in sorted(SKILLS_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        skill_key = f.stem
        if skill_key in disabled:
            continue
        try:
            mod_name = f"skills.{skill_key}"
            if mod_name in sys.modules:
                mod = importlib.reload(sys.modules[mod_name])
            else:
                mod = importlib.import_module(mod_name)
            if hasattr(mod, "SKILL_INFO") and hasattr(mod, "TOOLS") and hasattr(mod, "execute"):
                _skills[skill_key] = mod
                print(f"  ✅ Skill loaded: {mod.SKILL_INFO.get('icon','')} {mod.SKILL_INFO['name']}")
        except Exception as e:
            print(f"  ⚠️  Skill '{skill_key}' failed: {e}")

def get_tools():
    """Return all OpenAI tool definitions from loaded skills."""
    tools = []
    for mod in _skills.values():
        tools.extend(mod.TOOLS)
    return tools

def execute(tool_name, arguments):
    """Try to execute tool_name via a loaded skill. Returns None if not handled."""
    for mod in _skills.values():
        names = {t["function"]["name"] for t in mod.TOOLS}
        if tool_name in names:
            return mod.execute(tool_name, arguments)
    return None

def list_skills():
    """Return dict of loaded skill info."""
    return {k: mod.SKILL_INFO for k, mod in _skills.items()}

def list_all_skill_files():
    """Return all skill files (loaded or disabled)."""
    if not SKILLS_DIR.exists():
        return []
    return [f.stem for f in sorted(SKILLS_DIR.glob("*.py")) if not f.name.startswith("_")]

# Auto-load on import
load_skills()
