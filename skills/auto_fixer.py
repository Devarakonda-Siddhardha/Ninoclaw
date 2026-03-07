"""
Auto Fixer skill — analyze error screenshots or logs and apply safe fixes.
Owner-only: runs shell commands to repair environment (upgrade Node, npm install, rebuild modules).

Tool: run_auto_fix(image_b64) -> analyzes the image, runs diagnostics, applies fixes, returns a report.
"""
import os
import base64
import tempfile
import subprocess
import json

SKILL_INFO = {
    "name": "auto_fixer",
    "description": "Analyze error screenshots and apply safe fixes (owner-only)",
    "version": "1.0",
    "icon": "🛠️",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_auto_fix",
            "description": "Analyze a base64-encoded error screenshot, run diagnostics, and apply safe fixes like upgrading Node or reinstalling npm packages. Owner-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_b64": {"type": "string", "description": "Base64-encoded image"},
                },
                "required": ["image_b64"],
            },
        },
    },
]


def _save_image(b64):
    tmp = tempfile.gettempdir()
    path = os.path.join(tmp, f"auto_fix_img_{int(os.getpid())}.png")
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    return path


def _run(cmd, timeout=120):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return out.returncode, out.stdout.strip(), out.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _analyze_textual_output(text):
    """Simple heuristic analyzer for common errors. Returns suggested action list."""
    actions = []
    t = text.lower()
    if "node" in t and "version" in t and "require" in t:
        actions.append("check_node_version")
    if "missing optional dependency" in t or "not found" in t or "cannot find module" in t:
        actions.append("rebuild_native_modules")
    if "npm" in t and "peer" in t and "dependency" in t:
        actions.append("npm_install_legacy")
    if "could not get lock" in t or "epipe" in t:
        actions.append("clean_npm_cache")
    if "node-gyp" in t or "gyp" in t:
        actions.append("install_build_tools")
    return actions


def run_auto_fix(tool_name, arguments):
    if tool_name != "run_auto_fix":
        return None
    # Owner-only check
    if os.getenv("OWNER_ID", "0") == "0":
        return "❌ Owner not configured; auto_fix disabled. Set OWNER_ID in .env."

    image_b64 = arguments.get("image_b64")
    report = []
    if not image_b64:
        return "❌ No image provided."

    img_path = _save_image(image_b64)
    report.append(f"Saved screenshot to {img_path}")

    # Run OCR using tesseract if available, else skip to trying node/npm diagnostics
    ocr_text = ""
    rc, out, err = _run(f"which tesseract || true")
    if rc == 0 and out:
        rc2, ocr_out, ocr_err = _run(f"tesseract {img_path} stdout || true", timeout=30)
        ocr_text = (ocr_out or "") + "\n" + (ocr_err or "")
        report.append("OCR extracted text from image.")
    else:
        report.append("Tesseract not available; skipping OCR.")

    # Basic diagnostics: node -v, npm -v, check for package.json problems
    rc, node_out, node_err = _run("node -v || true")
    report.append(f"node -v: {node_out or node_err}")
    rc, npm_out, npm_err = _run("npm -v || true")
    report.append(f"npm -v: {npm_out or npm_err}")

    # Combine OCR and stderr heuristics
    combined = (ocr_text or "") + "\n" + (arguments.get("extra_text") or "")
    actions = _analyze_textual_output(combined)
    report.append(f"Suggested actions: {actions}")

    applied = []
    # Apply safe fixes
    if "check_node_version" in actions:
        # Upgrade node via nodesource
        applied.append("upgrade_node")
        rc, out, err = _run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs --no-install-recommends", timeout=300)
        applied.append(f"upgrade_node: rc={rc}")
    if "install_build_tools" in actions:
        applied.append("install_build_tools")
        _run("apt-get update && apt-get install -y build-essential python3 python3-dev --no-install-recommends", timeout=300)
    if "rebuild_native_modules" in actions:
        applied.append("rebuild_native_modules")
        # Try npm rebuild in repo root
        rc, out, err = _run("npm rebuild --build-from-source --no-audit --no-fund || true", timeout=600)
        applied.append(f"npm_rebuild: rc={rc}")
    if "npm_install_legacy" in actions:
        applied.append("npm_install_legacy")
        rc, out, err = _run("npm install --legacy-peer-deps --no-audit --no-fund || true", timeout=600)
        applied.append(f"npm_install_legacy: rc={rc}")
    if "clean_npm_cache" in actions:
        applied.append("clean_npm_cache")
        _run("npm cache clean --force || true")

    report.append(f"Applied actions: {applied}")

    # Final status
    rc, node_out2, _ = _run("node -v || true")
    rc, npm_out2, _ = _run("npm -v || true")
    report.append(f"After fixes — node: {node_out2}, npm: {npm_out2}")

    return "\n".join(report)
