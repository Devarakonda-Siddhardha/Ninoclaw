"""
Ninoclaw Setup Wizard — clean single-flow interactive CLI
"""
import os, sys, getpass, shutil
from runtime_capabilities import detect_capabilities, recommended_env_overrides, summarized_capability_report

_IS_WIN = sys.platform == "win32"
if _IS_WIN:
    import msvcrt
    try:
        import ctypes
        _kernel32 = ctypes.windll.kernel32
        _h = _kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        _mode = ctypes.c_uint()
        if _kernel32.GetConsoleMode(_h, ctypes.byref(_mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING for ANSI cursor/colors
            _kernel32.SetConsoleMode(_h, _mode.value | 0x0004)
    except Exception:
        pass
else:
    import tty, termios, select

G   = "\033[92m";  B  = "\033[94m";  Y  = "\033[93m"
R   = "\033[91m";  C  = "\033[96m";  W  = "\033[1;97m"
DIM = "\033[2m";   RST= "\033[0m";   M  = "\033[95m"
HIDE= "\033[?25l"; SHOW="\033[?25h"; UP = "\033[1A"; CLR="\033[2K"

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

BANNER = f"""{C}
  ███╗   ██╗██╗███╗   ██╗ ██████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ████╗  ██║██║████╗  ██║██╔═══██╗██╔════╝██║     ██╔══██╗██║    ██║
  ██╔██╗ ██║██║██╔██╗ ██║██║   ██║██║     ██║     ███████║██║ █╗ ██║
  ██║╚██╗██║██║██║╚██╗██║██║   ██║██║     ██║     ██╔══██║██║███╗██║
  ██║ ╚████║██║██║ ╚████║╚██████╔╝╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝{RST}
{DIM}  Personal AI Assistant — Setup Wizard{RST}
"""

# ── helpers ──────────────────────────────────────────────────────────────────

def _getch():
    if _IS_WIN:
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):  # special key prefix on Windows
            ch2 = msvcrt.getwch()
            # Map Windows arrow keys to ANSI escape sequences
            _map = {'H': '\x1b[A', 'P': '\x1b[B', 'K': '\x1b[D', 'M': '\x1b[C'}
            return _map.get(ch2, ch + ch2)
        return ch
    else:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = os.read(fd, 1).decode('latin-1')
            if ch == '\x1b':
                # wait up to 50ms for rest of escape sequence
                if select.select([fd], [], [], 0.05)[0]:
                    ch += os.read(fd, 2).decode('latin-1')
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _term_width():
    try:
        return shutil.get_terminal_size((100, 30)).columns
    except Exception:
        return 100


def _fit_line(text: str, pad: int = 10) -> str:
    """Trim long labels so each option stays on one console line."""
    max_len = max(20, _term_width() - pad)
    return text if len(text) <= max_len else (text[:max_len - 3] + "...")


def _pick_existing_url(existing: str, fallback: str, must_contain=(), any_contains=()):
    """Reuse an existing URL only if it matches expected provider patterns."""
    existing = (existing or "").strip()
    if existing:
        ok_all = all(k in existing for k in must_contain) if must_contain else True
        ok_any = any(k in existing for k in any_contains) if any_contains else True
        if ok_all and ok_any:
            return existing
    return fallback


def choose(prompt, options, default=0):
    """Arrow-key menu. options = list of (label, value)."""
    idx = default
    n   = len(options)
    print(f"\n  {W}{prompt}{RST}\n")
    for _ in options:
        print()
    sys.stdout.write(HIDE); sys.stdout.flush()

    def _render():
        for _ in range(n):
            sys.stdout.write(UP + "\r" + CLR)
        for i, (lbl, _) in enumerate(options):
            lbl = _fit_line(lbl)
            if i == idx:
                sys.stdout.write(f"\r  {G}❯ {W}{lbl}{RST}\n")
            else:
                sys.stdout.write(f"\r    {DIM}{lbl}{RST}\n")
        sys.stdout.flush()

    try:
        _render()
        while True:
            k = _getch()
            if   k in ('\x1b[A', '\x1b[D'): idx = (idx-1) % n
            elif k in ('\x1b[B', '\x1b[C'): idx = (idx+1) % n
            elif k in ('\r','\n',' '):       break
            elif k == '\x03':
                sys.stdout.write(SHOW); sys.exit(0)
            _render()
    finally:
        sys.stdout.write(SHOW); sys.stdout.flush()

    print(f"\n  {G}✓{RST}  {options[idx][0]}\n")
    return options[idx][1]


def ask(prompt, default=None, secret=False, optional=False):
    if default:
        shown_default = "saved" if secret else default
        hint = f" {DIM}[{shown_default}]{RST}"
    else:
        hint = f" {DIM}(optional - press Enter to skip){RST}" if optional else ""
    try:
        if secret:
            val = getpass.getpass(f"  {C}❯{RST} {prompt}{hint}: ")
        else:
            val = input(f"  {C}❯{RST} {prompt}{hint}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Y}Cancelled.{RST}"); sys.exit(0)
    val = (val or "").strip()
    if val:
        return val
    if default not in (None, ""):
        return default
    return None if optional else default

def section(title):
    print(f"\n{M}  ── {W}{title}{RST}")


def ok(msg): print(f"  {G}✔{RST}  {msg}")
def info(msg): print(f"  {DIM}  {msg}{RST}")


def load_existing_env():
    data = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    data[k.strip()] = v.strip().strip('"')
    return data


def test_api_key(api_url, api_key, model):
    """Test if the API key works by making a simple request."""
    if not api_key or api_key == "your-api-key-here":
        return False, "No API key provided"

    import requests
    try:
        url = f"{api_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)

        if resp.status_code == 401:
            return False, "Invalid API key"
        elif resp.status_code == 429:
            return False, "Rate limited (key might be valid)"
        elif resp.status_code >= 400:
            return False, f"API error: {resp.status_code}"
        else:
            return True, "API key is valid"
    except requests.RequestException as e:
        return False, f"Connection failed: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def save_env(data):
    lines = ["# Ninoclaw config - generated by wizard\n"]
    for k, v in data.items():
        if v:
            lines.append(f'{k}="{v}"\n')
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ── wizard ───────────────────────────────────────────────────────────────────

def run_wizard():
    e = load_existing_env()  # existing values
    capabilities = detect_capabilities(force_refresh=True)
    capability_report = summarized_capability_report(capabilities)
    print(BANNER)

    if e.get("TELEGRAM_BOT_TOKEN") and e["TELEGRAM_BOT_TOKEN"] != "YOUR_BOT_TOKEN_HERE":
        redo = choose("Existing config found. Re-run setup?",
                      [("Yes — reconfigure everything", True),
                       ("No  — keep current config",    False)])
        if not redo:
            return e

    # Preserve existing .env keys and only overwrite values changed in wizard.
    cfg = dict(e)

    # ── 1. Messaging Platforms ────────────────────────────────────────────────
    section("Step 1 — Messaging Platforms")

    _platforms = [
        ("Telegram   (recommended — most features)",   "telegram"),
        ("Discord    (@mention + DM support)",          "discord"),
    ]
    # Multi-select: toggle each platform
    selected = set()
    # Pre-select based on existing config
    if e.get("TELEGRAM_BOT_TOKEN") and e["TELEGRAM_BOT_TOKEN"] != "YOUR_BOT_TOKEN_HERE":
        selected.add("telegram")
    if e.get("DISCORD_BOT_TOKEN"):
        selected.add("discord")
    if not selected:
        selected.add("telegram")  # default

    # Multi-select menu
    print(f"\n  {W}Which platforms do you want to use?{RST}")
    info("Space = toggle  |  Enter = confirm  |  ↑↓ = move")
    n = len(_platforms)
    idx = 0

    def _render_platforms():
        for _ in range(n):
            sys.stdout.write(UP + "\r" + CLR)
        for i, (lbl, val) in enumerate(_platforms):
            lbl = _fit_line(lbl, pad=14)
            check = f"{G}◉{RST}" if val in selected else f"{DIM}○{RST}"
            cursor = f"{G}❯ {W}" if i == idx else f"    {DIM}"
            sys.stdout.write(f"\r  {cursor}{check}  {lbl}{RST}\n")
        sys.stdout.flush()

    for _ in _platforms:
        print()
    sys.stdout.write(HIDE); sys.stdout.flush()
    try:
        _render_platforms()
        while True:
            k = _getch()
            if k in ('\x1b[A', '\x1b[D'):
                idx = (idx - 1) % n
            elif k in ('\x1b[B', '\x1b[C'):
                idx = (idx + 1) % n
            elif k == ' ':
                val = _platforms[idx][1]
                if val in selected:
                    selected.discard(val)
                else:
                    selected.add(val)
            elif k in ('\r', '\n'):
                break
            elif k == '\x03':
                sys.stdout.write(SHOW); sys.exit(0)
            _render_platforms()
    finally:
        sys.stdout.write(SHOW); sys.stdout.flush()

    if not selected:
        print(f"  {Y}⚠  No platform selected — defaulting to Telegram{RST}")
        selected.add("telegram")

    print(f"\n  {G}✓{RST}  Platforms: {', '.join(sorted(selected))}\n")

    # ── 1a. Telegram token ────────────────────────────────────────────────────
    if "telegram" in selected:
        section("Step 1a — Telegram Bot Token")
        info("Get yours from @BotFather on Telegram")
        token = ask("Bot Token", default=e.get("TELEGRAM_BOT_TOKEN"), secret=True)
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            print(f"  {R}✗  Telegram token is required.{RST}"); sys.exit(1)
        cfg["TELEGRAM_BOT_TOKEN"] = token
        ok("Telegram token saved")
    else:
        cfg["TELEGRAM_BOT_TOKEN"] = e.get("TELEGRAM_BOT_TOKEN", "")

    # ── 1b. Discord token ─────────────────────────────────────────────────────
    if "discord" in selected:
        section("Step 1b — Discord Bot Token")
        info("Create bot: https://discord.com/developers/applications")
        info("Enable: Message Content Intent  |  Scope: bot + applications.commands")
        discord_token = ask("Discord Bot Token", default=e.get("DISCORD_BOT_TOKEN"), secret=True)
        if discord_token:
            cfg["DISCORD_BOT_TOKEN"] = discord_token
            ok("Discord token saved")
        else:
            print(f"  {Y}⚠  Skipped Discord (no token entered){RST}")
    else:
        cfg["DISCORD_BOT_TOKEN"] = e.get("DISCORD_BOT_TOKEN", "")

    # ── 2. AI Provider ────────────────────────────────────────────────────────
    section("Step 2 — AI Provider")
    provider = choose("Which AI provider?", [
        ("OpenRouter      (100+ models, free tier)",            "openrouter"),
        ("Google Gemini   (free tier)",                         "gemini"),
        ("Groq            (fast, free)",                        "groq"),
        ("OpenAI          (GPT-4o / GPT-4o-mini)",              "openai"),
        ("Mistral         (mistral-small)",                     "mistral"),
        ("xAI Grok        (grok-3-mini)",                       "xai"),
        ("ZhipuAI GLM     (glm-4-flash)",                       "glm"),
        ("ZhipuAI GLM Coding (glm-4.7 paid)",                   "glm_coding"),
        ("Anthropic Claude",                                    "anthropic"),
        ("Ollama          (local offline)",                     "ollama"),
        ("Local Server    (OpenAI-compatible)",                 "local"),
        ("Custom endpoint (manual URL)",                        "custom"),
    ])

    if provider == "openrouter":
        info("Get key: https://openrouter.ai/keys  (free signup)")
        info("Free models end with :free  e.g.  google/gemini-2.0-flash-exp:free")
        cfg["OPENAI_API_URL"] = "https://openrouter.ai/api/v1"
        key_default = e.get("OPENROUTER_API_KEY") or (e.get("OPENAI_API_KEY") if "openrouter.ai" in (e.get("OPENAI_API_URL", "")) else "")
        cfg["OPENAI_API_KEY"] = ask("OpenRouter API Key", default=key_default, secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "google/gemini-2.0-flash-exp:free")) or ""
        cfg["OPENROUTER_API_KEY"] = cfg["OPENAI_API_KEY"]

    elif provider == "gemini":
        info("Get key: https://aistudio.google.com/app/apikey")
        gemini_api_key = ask("Gemini API Key", default=e.get("OPENAI_API_KEY"), secret=True) or ""
        cfg["OPENAI_API_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai"
        cfg["OPENAI_API_KEY"] = gemini_api_key

        # Model selection with arrow keys
        gemini_models = [
            ("gemini-3-flash-preview (Fastest, recommended)", "gemini-3-flash-preview"),
            ("gemini-3-flash-thinking-preview", "gemini-3-flash-thinking-preview"),
            ("gemini-3-pro-preview", "gemini-3-pro-preview"),
            ("gemini-3-flash-exp", "gemini-3-flash-exp"),
            ("gemini-2.5-pro-preview-04-17", "gemini-2.5-pro-preview-04-17"),
            ("gemini-2.5-flash-preview-04-17", "gemini-2.5-flash-preview-04-17"),
            ("gemini-1.5-pro-preview-0514", "gemini-1.5-pro-preview-0514"),
            ("gemini-1.5-flash-preview-0514", "gemini-1.5-flash-preview-0514"),
        ]
        cfg["OPENAI_MODEL"] = choose("Select Gemini model", gemini_models, default=0)

        # Test the API key
        if gemini_api_key and gemini_api_key != "your-api-key-here":
            info("Testing API key...")
            valid, msg = test_api_key(cfg["OPENAI_API_URL"], cfg["OPENAI_API_KEY"], cfg["OPENAI_MODEL"])
            if valid:
                ok(f"API key is valid ✅")
            else:
                print(f"  {Y}⚠  {msg}{RST}")
                print(f"  {Y}⚠  Continuing anyway, but the bot may not work.{RST}")

    elif provider == "groq":
        info("Get key: https://console.groq.com")
        cfg["OPENAI_API_URL"] = "https://api.groq.com/openai/v1"
        key_default = e.get("GROQ_API_KEY") or (e.get("OPENAI_API_KEY") if "api.groq.com" in (e.get("OPENAI_API_URL", "")) else "")
        cfg["OPENAI_API_KEY"] = ask("Groq API Key", default=key_default, secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "llama-3.3-70b-versatile")) or ""
        cfg["GROQ_API_KEY"] = cfg["OPENAI_API_KEY"]

    elif provider == "openai":
        cfg["OPENAI_API_URL"] = "https://api.openai.com/v1"
        cfg["OPENAI_API_KEY"] = ask("OpenAI API Key", default=e.get("OPENAI_API_KEY"), secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "gpt-4o-mini")) or ""

    elif provider == "mistral":
        cfg["OPENAI_API_URL"] = "https://api.mistral.ai/v1"
        key_default = e.get("MISTRAL_API_KEY") or (e.get("OPENAI_API_KEY") if "api.mistral.ai" in (e.get("OPENAI_API_URL", "")) else "")
        cfg["OPENAI_API_KEY"] = ask("Mistral API Key", default=key_default, secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "mistral-small-latest")) or ""
        cfg["MISTRAL_API_KEY"] = cfg["OPENAI_API_KEY"]

    elif provider == "xai":
        cfg["OPENAI_API_URL"] = "https://api.x.ai/v1"
        key_default = e.get("XAI_API_KEY") or (e.get("OPENAI_API_KEY") if "api.x.ai" in (e.get("OPENAI_API_URL", "")) else "")
        cfg["OPENAI_API_KEY"] = ask("xAI API Key", default=key_default, secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "grok-3-mini")) or ""
        cfg["XAI_API_KEY"] = cfg["OPENAI_API_KEY"]

    elif provider == "glm":
        cfg["OPENAI_API_URL"] = "https://open.bigmodel.cn/api/paas/v4"
        key_default = e.get("GLM_API_KEY") or (e.get("OPENAI_API_KEY") if "open.bigmodel.cn" in (e.get("OPENAI_API_URL", "")) else "")
        cfg["OPENAI_API_KEY"] = ask("ZhipuAI API Key", default=key_default, secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "glm-4-flash")) or ""
        cfg["GLM_API_KEY"] = cfg["OPENAI_API_KEY"]

    elif provider == "glm_coding":
        info("Get key: https://z.ai  (GLM Coding Plan from $3/month)")
        cfg["OPENAI_API_URL"] = "https://api.z.ai/api/coding/paas/v4"
        key_default = e.get("GLM_CODING_API_KEY") or (e.get("OPENAI_API_KEY") if "api.z.ai" in (e.get("OPENAI_API_URL", "")) else "")
        cfg["OPENAI_API_KEY"] = ask("Z.AI API Key", default=key_default, secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "glm-4.7")) or ""
        cfg["GLM_CODING_API_KEY"]   = cfg["OPENAI_API_KEY"]
        cfg["GLM_CODING_MODEL"]     = cfg["OPENAI_MODEL"]

    elif provider == "anthropic":
        cfg["OPENAI_API_URL"] = "https://api.anthropic.com/v1"
        cfg["OPENAI_API_KEY"] = ask("Anthropic API Key", default=e.get("OPENAI_API_KEY"), secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "claude-3-5-sonnet-20241022")) or ""

    elif provider == "ollama":
        info("Make sure Ollama is running: ollama serve")
        cfg["OPENAI_API_URL"] = _pick_existing_url(
            e.get("OPENAI_API_URL", ""),
            "http://localhost:11434/v1",
            any_contains=("localhost:11434", "127.0.0.1:11434"),
        )
        info(f"Using endpoint: {cfg['OPENAI_API_URL']}  (preloaded)")
        cfg["OPENAI_API_KEY"] = "ollama"
        cfg["OPENAI_MODEL"]   = ask("Model", default=e.get("OPENAI_MODEL", "llama3.2")) or ""

    elif provider == "local":
        info("Make sure your local server is running (e.g. llama-server -hf ... --port 8000)")
        cfg["OPENAI_API_URL"] = _pick_existing_url(
            e.get("OPENAI_API_URL", ""),
            "http://127.0.0.1:8000/v1",
            any_contains=("127.0.0.1", "localhost"),
            must_contain=("/v1",),
        )
        info(f"Using endpoint: {cfg['OPENAI_API_URL']}  (preloaded)")
        cfg["OPENAI_API_KEY"] = ask("API Key (usually 'local')", default="local") or "local"
        cfg["OPENAI_MODEL"]   = ask("Model name (usually ignored by local servers)", default="local-model") or "local-model"

    else:  # custom
        cfg["OPENAI_API_URL"] = ask("API Base URL", default=e.get("OPENAI_API_URL")) or ""
        cfg["OPENAI_API_KEY"] = ask("API Key", default=e.get("OPENAI_API_KEY"), secret=True) or ""
        cfg["OPENAI_MODEL"]   = ask("Model name", default=e.get("OPENAI_MODEL")) or ""

    ok(f"Provider: {provider}  |  Model: {cfg['OPENAI_MODEL']}")

    # ── 3. Fallback providers ─────────────────────────────────────────────────
    section("Step 3 - Fallback Providers (optional)")
    info("Pick as many fallback providers as you want. Space = toggle | Enter = confirm")
    info("Tip: highlight 'Continue without fallbacks' and press Enter to skip this step")

    fallback_specs = [
        {
            "id": "openrouter",
            "label": "OpenRouter (100+ models)",
            "key_env": "OPENROUTER_API_KEY",
            "model_env": "OPENROUTER_MODEL",
            "default_model": "openai/gpt-4o-mini",
            "key_prompt": "OpenRouter API Key",
            "model_prompt": "OpenRouter model",
            "hint": "Get key: https://openrouter.ai/keys",
        },
        {
            "id": "groq",
            "label": "Groq (fast, free tier)",
            "key_env": "GROQ_API_KEY",
            "model_env": "GROQ_MODEL",
            "default_model": "llama-3.3-70b-versatile",
            "key_prompt": "Groq API Key",
            "model_prompt": "Groq model",
            "hint": "Get key: https://console.groq.com",
        },
        {
            "id": "mistral",
            "label": "Mistral",
            "key_env": "MISTRAL_API_KEY",
            "model_env": "MISTRAL_MODEL",
            "default_model": "mistral-small-latest",
            "key_prompt": "Mistral API Key",
            "model_prompt": "Mistral model",
            "hint": "Get key: https://console.mistral.ai",
        },
        {
            "id": "xai",
            "label": "xAI Grok",
            "key_env": "XAI_API_KEY",
            "model_env": "XAI_MODEL",
            "default_model": "grok-3-mini",
            "key_prompt": "xAI API Key",
            "model_prompt": "xAI model",
            "hint": "Get key: https://console.x.ai",
        },
        {
            "id": "glm",
            "label": "ZhipuAI GLM",
            "key_env": "GLM_API_KEY",
            "model_env": "GLM_MODEL",
            "default_model": "glm-4-flash",
            "key_prompt": "GLM API Key",
            "model_prompt": "GLM model",
            "hint": "Get key: https://open.bigmodel.cn",
        },
        {
            "id": "glm_coding",
            "label": "Z.AI GLM Coding",
            "key_env": "GLM_CODING_API_KEY",
            "model_env": "GLM_CODING_MODEL",
            "default_model": "glm-4.7",
            "key_prompt": "Z.AI API Key",
            "model_prompt": "GLM Coding model",
            "hint": "Get key: https://z.ai",
        },
        {
            "id": "ollama",
            "label": "Ollama (local model)",
            "key_env": "",
            "model_env": "OLLAMA_MODEL",
            "default_model": "llama3.2",
            "key_prompt": "",
            "model_prompt": "Ollama fallback model",
            "hint": "Run local server first: ollama serve",
        },
    ]

    fallback_specs = [s for s in fallback_specs if s["id"] != provider]
    fallback_options = [(s["label"], s["id"]) for s in fallback_specs]
    fallback_options.append(("Continue without fallbacks", "__skip__"))

    preselected_fallbacks = []
    for spec in fallback_specs:
        key_env = spec["key_env"]
        model_env = spec["model_env"]
        pick = False
        if key_env:
            if e.get(key_env):
                pick = True
        elif e.get(model_env):
            pick = True
        if pick and spec["id"] not in preselected_fallbacks:
            preselected_fallbacks.append(spec["id"])

    selected_fallbacks = set(preselected_fallbacks)
    idx = 0
    n_fallbacks = len(fallback_options)

    def _render_fallbacks():
        for _ in range(n_fallbacks):
            sys.stdout.write(UP + "\r" + CLR)
        for i, (lbl, val) in enumerate(fallback_options):
            lbl = _fit_line(lbl, pad=14)
            check = f"{G}◉{RST}" if val in selected_fallbacks else f"{DIM}○{RST}"
            cursor = f"{G}❯ {W}" if i == idx else f"    {DIM}"
            sys.stdout.write(f"\r  {cursor}{check}  {lbl}{RST}\n")
        sys.stdout.flush()

    for _ in fallback_options:
        print()
    sys.stdout.write(HIDE); sys.stdout.flush()
    try:
        _render_fallbacks()
        while True:
            k = _getch()
            if k in ('\x1b[A', '\x1b[D'):
                idx = (idx - 1) % n_fallbacks
            elif k in ('\x1b[B', '\x1b[C'):
                idx = (idx + 1) % n_fallbacks
            elif k == ' ':
                val = fallback_options[idx][1]
                if val == "__skip__":
                    pass
                elif val in selected_fallbacks:
                    selected_fallbacks.discard(val)
                else:
                    selected_fallbacks.add(val)
            elif k in ('\r', '\n'):
                if fallback_options[idx][1] == "__skip__":
                    selected_fallbacks.clear()
                elif not selected_fallbacks and fallback_options:
                    selected_fallbacks.add(fallback_options[idx][1])
                break
            elif k == '\x03':
                sys.stdout.write(SHOW); sys.exit(0)
            _render_fallbacks()
    finally:
        sys.stdout.write(SHOW); sys.stdout.flush()

    fallback_order = [val for _, val in fallback_options if val != "__skip__" and val in selected_fallbacks]
    if fallback_order:
        ok(f"Fallbacks selected: {', '.join(fallback_order)}")
    else:
        ok("No fallback selected")

    # Disable unselected fallback providers to keep behavior clear.
    for spec in fallback_specs:
        if spec["id"] in selected_fallbacks:
            continue
        if spec["key_env"]:
            cfg.pop(spec["key_env"], None)
        if spec["model_env"]:
            cfg.pop(spec["model_env"], None)

    # Ask credentials/models only for selected fallback providers.
    fallback_spec_by_id = {s["id"]: s for s in fallback_specs}
    for fallback_id in fallback_order:
        spec = fallback_spec_by_id[fallback_id]
        info(spec["hint"])
        if spec["key_env"]:
            key_val = ask(spec["key_prompt"], default=e.get(spec["key_env"]), secret=True, optional=True)
            if not key_val:
                print(f"  {Y}⚠  Skipping {fallback_id} (no key provided){RST}")
                continue
            cfg[spec["key_env"]] = key_val
        model_default = e.get(spec["model_env"], spec["default_model"])
        model_val = ask(spec["model_prompt"], default=model_default, optional=True) or spec["default_model"]
        cfg[spec["model_env"]] = model_val

    # ── 4. Web Search ─────────────────────────────────────────────────────────
    section("Step 4 — Web Search  (optional)")
    info("Free at https://serper.dev — 2500 searches/month")
    serper = ask("Serper API Key", default=e.get("SERPER_API_KEY"), optional=True, secret=True)
    if serper:
        cfg["SERPER_API_KEY"] = serper
        ok("Web search enabled")
    else:
        ok("Skipped")

    # ── 5. Owner ID ───────────────────────────────────────────────────────────
    section("Step 5 — Your Telegram User ID  (recommended)")
    info("Message @userinfobot on Telegram to get your ID")
    owner = ask("Your Telegram user ID", default=e.get("OWNER_ID"), optional=True)
    if owner:
        cfg["OWNER_ID"] = owner
        ok(f"Owner locked to {owner}")
    else:
        ok("Skipped")

    # ── 6. Personalization ────────────────────────────────────────────────────
    section("Step 6 — Personalization")
    cfg["AGENT_NAME"]  = ask("Bot name",    default=e.get("AGENT_NAME",  "Ninoclaw")) or "Ninoclaw"
    cfg["USER_NAME"]   = ask("Your name",   default=e.get("USER_NAME",   "friend"))   or "friend"
    cfg["BOT_PURPOSE"] = ask("Bot purpose", default=e.get("BOT_PURPOSE", "be your personal AI assistant")) or "be your personal AI assistant"
    cfg["TIMEZONE"]    = ask("Timezone",    default=e.get("TIMEZONE",    "UTC"))       or "UTC"
    ok(f"{cfg['AGENT_NAME']} ready for {cfg['USER_NAME']} ({cfg['TIMEZONE']})")

    # ── 7. Email (Resend) ─────────────────────────────────────────────────────
    section("Step 7 — Email via Resend  (optional)")
    info("Free at https://resend.com — 100 emails/day")
    resend_key = ask("Resend API Key", default=e.get("RESEND_API_KEY"), optional=True, secret=True)
    if resend_key:
        cfg["RESEND_API_KEY"] = resend_key
        cfg["RESEND_FROM"]    = ask("From address", default=e.get("RESEND_FROM", "onboarding@resend.dev")) or ""
        cfg["OWNER_EMAIL"]    = ask("Your email",   default=e.get("OWNER_EMAIL")) or ""
        ok("Resend configured — load skill in Telegram to activate")
    else:
        ok("Skipped")

    # ── 8. Image Generation ───────────────────────────────────────────────────
    section("Step 8 — Image Generation  (optional)")
    info("Free option: HuggingFace (FLUX.1-schnell) — get token at https://huggingface.co/settings/tokens")
    info("Fallback: Google Gemini Nano Banana — get key at https://aistudio.google.com/apikey")
    hf_token = ask("HuggingFace Token (free, recommended)", default=e.get("HF_TOKEN"), optional=True, secret=True)
    if hf_token:
        cfg["HF_TOKEN"] = hf_token
        ok("HuggingFace FLUX.1-schnell enabled — say 'generate an image of...' in Telegram")
    else:
        ok("Skipped HuggingFace")
    # Gemini fallback
    is_gemini = "generativelanguage.googleapis.com" in cfg.get("OPENAI_API_URL", e.get("OPENAI_API_URL", ""))
    if is_gemini:
        info("Gemini fallback: reusing your existing Gemini API key ✅")
        cfg["GEMINI_API_KEY"] = cfg.get("OPENAI_API_KEY") or e.get("OPENAI_API_KEY", "")
    else:
        gemini_key = ask("Gemini API Key (fallback, optional)", default=e.get("GEMINI_API_KEY"), optional=True, secret=True)
        if gemini_key:
            cfg["GEMINI_API_KEY"] = gemini_key

    # ── 9. Dashboard ──────────────────────────────────────────────────────────
    section("Step 9 — Web Dashboard")
    cfg["DASHBOARD_PASSWORD"] = ask("Dashboard password", default=e.get("DASHBOARD_PASSWORD", "admin")) or "admin"
    cfg["DASHBOARD_PORT"]     = ask("Dashboard port",     default=e.get("DASHBOARD_PORT", "8080"))       or "8080"
    ok(f"Dashboard at http://localhost:{cfg['DASHBOARD_PORT']}")

    # ── 10. Compatibility Profile ─────────────────────────────────
    section("Step 10 — Device Compatibility Profile")
    info(f"Detected device: {capability_report['device']}")
    info(f"Runtime profile: {capability_report['profile']}  |  RAM: {capability_report['ram_gb']} GB")
    overrides = recommended_env_overrides(cfg, capabilities)
    cfg.update(overrides)
    disabled_skills = [s for s in overrides.get("DISABLED_SKILLS", "").split(",") if s]
    if disabled_skills:
        ok(f"Auto-disabled incompatible skills: {', '.join(disabled_skills)}")
    else:
        ok("No compatibility-based skill disables needed")

    # ── Save ──────────────────────────────────────────────────────────────────
    save_env(cfg)
    print(f"\n{G}  ✔  Config saved to .env{RST}")
    print(f"{C}  🦀 Run: ninoclaw start{RST}\n")
    return cfg


def needs_setup():
    e = load_existing_env()
    token = e.get("TELEGRAM_BOT_TOKEN", "")
    discord = e.get("DISCORD_BOT_TOKEN", "")
    has_telegram = token and token != "YOUR_BOT_TOKEN_HERE"
    has_discord  = bool(discord)
    return not has_telegram and not has_discord


if __name__ == "__main__":
    run_wizard()
