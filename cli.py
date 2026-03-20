"""
Ninoclaw CLI — command line interface for managing the assistant
"""
import os
import sys
import subprocess

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Colors
G   = "\033[92m"
B   = "\033[94m"
Y   = "\033[93m"
R   = "\033[91m"
C   = "\033[96m"
M   = "\033[95m"
W   = "\033[1;97m"
DIM = "\033[2m"
RST = "\033[0m"

HELP = f"""
{C}🦀 Ninoclaw CLI{RST}

{W}Usage:{RST}
  ninoclaw {B}<command>{RST} [options]

{W}Commands:{RST}
  {G}start{RST}              Start the bot (default)
  {G}setup{RST}              Run the setup wizard (first-time config)
  {G}onboard{RST}            Alias for setup
  {G}reset{RST}              Delete config and re-run setup wizard
  {G}status{RST}             Show current configuration and status
  {G}update{RST}             Pull latest code from GitHub and restart
  {G}memory{RST}             Memory management
    {DIM}clear [user_id]{RST}    Clear chat history (all users or specific)
    {DIM}stats{RST}             Show memory usage stats
  {G}dashboard{RST}          Start the web dashboard (default port 8080)
  {G}model{RST}              Show or change the AI model
    {DIM}ninoclaw model{RST}          Show current model
    {DIM}ninoclaw model <name>{RST}   Switch to a different model
  {G}route{RST}             Smart model routing (fast vs smart)
    {DIM}ninoclaw route{RST}                  Show routing config
    {DIM}ninoclaw route fast <model>{RST}     Set fast model (simple tasks)
    {DIM}ninoclaw route smart <model>{RST}    Set smart model (complex tasks)
    {DIM}ninoclaw route off{RST}              Disable routing
  {G}think{RST}              Toggle Ollama thinking mode (Qwen3 only)
    {DIM}ninoclaw think{RST}          Show current state
    {DIM}ninoclaw think on|off{RST}   Enable/disable thinking
  {G}integrations{RST}       Manage third-party integrations
    {DIM}ninoclaw integrations{RST}                          List all integrations & key status
    {DIM}ninoclaw integrations slack <webhook_url>{RST}      Save SLACK_WEBHOOK_URL
    {DIM}ninoclaw integrations github <token>{RST}           Save GITHUB_TOKEN
    {DIM}ninoclaw integrations spotify <id> <secret> <rt>{RST} Save Spotify credentials
    {DIM}ninoclaw integrations gcal <path/to/creds.json>{RST} Save Google Calendar credentials path
  {G}version{RST}            Show current version (git commit)

{W}Examples:{RST}
  {DIM}ninoclaw{RST}                    Start the bot
  {DIM}ninoclaw setup{RST}              Configure API keys, model, etc.
  {DIM}ninoclaw reset{RST}              Wipe config and start fresh
  {DIM}ninoclaw status{RST}             Check what's configured
  {DIM}ninoclaw memory clear{RST}       Clear all conversations
  {DIM}ninoclaw memory stats{RST}       Show how much is stored
"""

REPO_DIR = os.path.dirname(__file__)
REQUIREMENTS_FILE = os.path.join(REPO_DIR, "requirements.txt")
REQUIREMENTS_STAMP = os.path.join(REPO_DIR, ".requirements.installed")


def _requirements_stamp_value():
    try:
        return str(int(os.path.getmtime(REQUIREMENTS_FILE)))
    except OSError:
        return None


def ensure_requirements_installed():
    """Install Python dependencies when requirements.txt is new or changed."""
    if not os.path.exists(REQUIREMENTS_FILE):
        return True

    expected = _requirements_stamp_value()
    current = None
    if os.path.exists(REQUIREMENTS_STAMP):
        try:
            with open(REQUIREMENTS_STAMP, "r", encoding="utf-8") as f:
                current = f.read().strip()
        except OSError:
            current = None

    if expected and current == expected:
        return True

    print(f"{C}Installing Python dependencies from requirements.txt...{RST}")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
        cwd=REPO_DIR,
    )
    if result.returncode != 0:
        print(f"{R}Failed to install requirements.txt dependencies.{RST}")
        return False

    try:
        with open(REQUIREMENTS_STAMP, "w", encoding="utf-8") as f:
            f.write(expected or "installed")
    except OSError:
        pass

    print(f"{G}Dependencies are ready.{RST}\n")
    return True


def cmd_start():
    """Start the Ninoclaw bot"""
    if not ensure_requirements_installed():
        sys.exit(1)

    from wizard import needs_setup, run_wizard
    if needs_setup():
        print(f"{Y}⚠  No config found — running setup wizard first...{RST}\n")
        run_wizard()
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

    # Import here so env is fully loaded
    import main as _main
    _main.main()


def cmd_setup():
    """Run setup wizard"""
    if not ensure_requirements_installed():
        sys.exit(1)

    from wizard import run_wizard
    run_wizard()
    print(f"{G}✔  Setup complete. Run {W}ninoclaw start{G} to launch.{RST}\n")


def cmd_reset():
    """Delete .env and re-run wizard"""
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        confirm = input(f"  {R}⚠  Delete config and start fresh?{RST} (yes/N): ").strip().lower()
        if confirm != "yes":
            print(f"  {Y}Cancelled.{RST}")
            return
        os.remove(env_file)
        print(f"  {G}✔  Config deleted.{RST}\n")
    from wizard import run_wizard
    run_wizard()


def cmd_status():
    """Show current config status"""
    from wizard import load_existing_env
    env = load_existing_env()

    def masked(val):
        if not val or len(val) < 8:
            return f"{R}Not set{RST}"
        return f"{G}{val[:6]}...{val[-4:]}{RST}"

    def checkmark(val):
        return f"{G}✔  Set{RST}" if val else f"{R}✗  Not set{RST}"

    print(f"""
{C}🦀 Ninoclaw Status{RST}
{DIM}{'─'*40}{RST}
  {W}Telegram Token{RST}   {checkmark(env.get('TELEGRAM_BOT_TOKEN'))}
  {W}Primary Model{RST}    {G}{env.get('OPENAI_MODEL', 'Not set')}{RST}
  {W}API Key{RST}          {masked(env.get('OPENAI_API_KEY'))}
  {W}API URL{RST}          {DIM}{env.get('OPENAI_API_URL', 'Not set')}{RST}
  {W}Fallback Model{RST}   {env.get('FALLBACK_MODEL') or f'{DIM}None{RST}'}
  {W}Web Search{RST}       {checkmark(env.get('SERPER_API_KEY'))}
  {W}Owner ID{RST}         {env.get('OWNER_ID') or f'{Y}Not set (open){RST}'}
{DIM}{'─'*40}{RST}""")

    # DB stats
    try:
        import sqlite3
        db = os.path.join(os.path.dirname(__file__), "ninoclaw.db")
        if os.path.exists(db):
            conn = sqlite3.connect(db)
            msgs  = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM conversations").fetchone()[0]
            tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed=0").fetchone()[0]
            crons = conn.execute("SELECT COUNT(*) FROM cron_jobs WHERE is_active=1").fetchone()[0]
            conn.close()
            print(f"  {W}Messages stored{RST}  {msgs} across {users} user(s)")
            print(f"  {W}Pending tasks{RST}    {tasks}")
            print(f"  {W}Active crons{RST}     {crons}")
        else:
            print(f"  {DIM}No database yet — will be created on first run.{RST}")
    except Exception:
        pass

    # Git version
    try:
        import subprocess
        commit = subprocess.run(["git","rev-parse","--short","HEAD"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)).stdout.strip()
        print(f"  {W}Version{RST}          {DIM}{commit}{RST}")
    except Exception:
        pass
    print()


def cmd_memory(args):
    """Memory subcommands"""
    sub = args[0] if args else "help"

    if sub == "clear":
        import sqlite3
        db = os.path.join(os.path.dirname(__file__), "ninoclaw.db")
        if not os.path.exists(db):
            print(f"  {Y}No database found.{RST}")
            return
        conn = sqlite3.connect(db)
        if len(args) > 1:
            uid = args[1]
            conn.execute("DELETE FROM conversations WHERE user_id=?", (uid,))
            conn.commit()
            print(f"  {G}✔  Cleared memory for user {uid}.{RST}")
        else:
            confirm = input(f"  {R}⚠  Clear ALL conversations for ALL users?{RST} (yes/N): ").strip().lower()
            if confirm == "yes":
                conn.execute("DELETE FROM conversations")
                conn.commit()
                print(f"  {G}✔  All conversations cleared.{RST}")
            else:
                print(f"  {Y}Cancelled.{RST}")
        conn.close()

    elif sub == "stats":
        import sqlite3
        db = os.path.join(os.path.dirname(__file__), "ninoclaw.db")
        if not os.path.exists(db):
            print(f"  {Y}No database found.{RST}")
            return
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT user_id, COUNT(*) as c FROM conversations GROUP BY user_id ORDER BY c DESC"
        ).fetchall()
        conn.close()
        print(f"\n{C}  Memory Stats{RST}")
        print(f"  {DIM}{'─'*30}{RST}")
        if not rows:
            print(f"  {DIM}No conversations yet.{RST}")
        for uid, count in rows:
            print(f"  User {W}{uid}{RST}  →  {G}{count}{RST} messages")
        print()

    else:
        print(f"\n  {W}ninoclaw memory{RST} subcommands:")
        print(f"    {G}clear{RST} [user_id]   Clear conversations")
        print(f"    {G}stats{RST}              Show per-user message counts\n")


def cmd_update():
    """Pull latest code and restart"""
    from updater import check_for_updates, do_update, get_current_version, restart
    print(f"\n{C}🔍 Checking for updates...{RST} (current: {DIM}{get_current_version()}{RST})\n")
    has_updates, commits = check_for_updates()
    if not has_updates:
        print(f"{G}✔  Already on the latest version!{RST}\n")
        return
    print(f"{Y}📦 New changes:{RST}\n{DIM}{commits}{RST}\n")
    confirm = input(f"  Apply update? (Y/n): ").strip().lower()
    if confirm == "n":
        print(f"  {Y}Cancelled.{RST}")
        return
    success, msg = do_update()
    if not success:
        print(f"{R}✗  Update failed:{RST}\n{msg}")
        return
    print(f"\n{G}✔  Update complete! Restarting...{RST}\n")
    restart()


def cmd_dashboard():
    """Start the web dashboard"""
    from dashboard import run_dashboard
    run_dashboard()


def cmd_version():
    """Show current git version"""
    try:
        import subprocess
        commit = subprocess.run(["git","rev-parse","--short","HEAD"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)).stdout.strip()
        branch = subprocess.run(["git","rev-parse","--abbrev-ref","HEAD"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)).stdout.strip()
        print(f"\n{C}🦀 Ninoclaw{RST}  {W}{commit}{RST}  {DIM}({branch}){RST}\n")
    except Exception:
        print(f"{R}Could not determine version.{RST}")


def cmd_model(args):
    """Show or switch the AI model"""
    from dotenv import dotenv_values, set_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env = dotenv_values(env_path)
    current = env.get("OPENAI_MODEL", "gemini-3-flash-preview")

    if not args:
        # Show current + suggestions
        print(f"\n{C}🤖 Current model:{RST} {W}{current}{RST}")
        print(f"\n{DIM}Suggested models:{RST}")
        suggestions = [
            ("gemini-3-flash-preview",        "Google  — latest, fast"),
            ("gemini-2.5-flash-preview-04-17","Google  — stable preview"),
            ("gemini-2.0-flash-exp",          "Google  — free tier"),
            ("gpt-4o-mini",                   "OpenAI  — affordable"),
            ("gpt-4o",                        "OpenAI  — best quality"),
            ("mistral-small-latest",          "Mistral — free tier"),
            ("llama3.2",                      "Ollama  — local/offline"),
        ]
        for name, desc in suggestions:
            marker = f"{G}●{RST}" if name == current else f"{DIM}○{RST}"
            print(f"  {marker} {W}{name:<40}{RST} {DIM}{desc}{RST}")
        print(f"\n{DIM}Usage: ninoclaw model <name>{RST}\n")
        return

    new_model = args[0].strip()
    set_key(env_path, "OPENAI_MODEL", new_model)
    print(f"\n{G}✔  Model switched:{RST} {W}{new_model}{RST}")
    print(f"{DIM}Restart the bot for changes to take effect: ninoclaw start{RST}\n")


def cmd_imagegen(args):
    """Set up or show image generation config"""
    from dotenv import dotenv_values, set_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env = dotenv_values(env_path)
    fal_key    = env.get("FAL_KEY", "")
    hf_token   = env.get("HF_TOKEN", "")
    gemini_key = env.get("GEMINI_API_KEY", "")

    def clean_value(val):
        """Strip quotes from values to prevent credential issues"""
        val = val.strip()
        # Remove both single and double quotes from start/end
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        elif val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        return val

    if not args:
        print(f"\n{C}🎨 Image Generation{RST}")
        if fal_key:
            print(f"  {G}●{RST} fal.ai (FLUX)         — {fal_key[:8]}...  {G}✓ primary{RST}")
        else:
            print(f"  {R}○{RST} fal.ai (FLUX)         — not set")
        if hf_token:
            print(f"  {G}●{RST} HuggingFace (FLUX.1)  — {hf_token[:8]}...  {G}✓ free{RST}")
        else:
            print(f"  {DIM}○ HuggingFace (FLUX.1) — not set  (free at huggingface.co){RST}")
        if gemini_key:
            print(f"  {G}●{RST} Gemini Nano Banana     — {gemini_key[:8]}...  {DIM}(fallback){RST}")
        else:
            print(f"  {DIM}○ Gemini Nano Banana     — not set (fallback){RST}")
        if not fal_key and not hf_token and not gemini_key:
            print(f"\n  {DIM}Recommended: get a free HF token at https://huggingface.co/settings/tokens")
            print(f"  Usage: ninoclaw imagegen hf <token>")
            print(f"         ninoclaw imagegen fal <key>")
            print(f"         ninoclaw imagegen gemini <key>{RST}")
        print()
        return

    if len(args) < 2:
        print(f"\n{R}Usage: ninoclaw imagegen hf|fal|gemini <api-key>{RST}\n")
        return

    provider, key = args[0].lower(), clean_value(args[1])
    if provider in ("hf", "huggingface"):
        set_key(env_path, "HF_TOKEN", key)
        print(f"\n{G}✔  HuggingFace token saved{RST} — FLUX.1-schnell enabled (free)")
    elif provider == "fal":
        set_key(env_path, "FAL_KEY", key)
        print(f"\n{G}✔  fal.ai key saved{RST} — FLUX.1 Schnell enabled")
    elif provider == "gemini":
        set_key(env_path, "GEMINI_API_KEY", key)
        print(f"\n{G}✔  Gemini key saved{RST} — Nano Banana enabled (fallback)")
    else:
        print(f"\n{R}Usage: ninoclaw imagegen hf|fal|gemini <api-key>{RST}\n")
        return
    print(f"{DIM}Restart the bot: ninoclaw start{RST}\n")



    """Show or configure smart model routing (fast vs smart model)"""
    from dotenv import dotenv_values, set_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env = dotenv_values(env_path)
    fast  = env.get("FAST_MODEL", "")
    smart = env.get("SMART_MODEL", "") or env.get("OPENAI_MODEL", "")

    if not args:
        print(f"\n{C}🔀 Model Routing{RST}")
        if fast:
            print(f"  {G}●{RST} Enabled")
            print(f"  {W}Fast  (simple tasks):{RST} {fast}")
            print(f"  {W}Smart (complex tasks):{RST} {smart}")
            print(f"\n  {DIM}Simple = casual chat, quick questions")
            print(f"  Complex = code, research, long writing, analysis{RST}")
        else:
            print(f"  {R}●{RST} Disabled — single model for all tasks")
            print(f"  {DIM}Set a FAST_MODEL to enable routing{RST}")
        print(f"\n{DIM}Usage:")
        print(f"  ninoclaw route fast <model>   Set fast model")
        print(f"  ninoclaw route smart <model>  Set smart model")
        print(f"  ninoclaw route off            Disable routing{RST}\n")
        return

    sub = args[0].lower()
    if sub == "fast" and len(args) > 1:
        set_key(env_path, "FAST_MODEL", args[1])
        print(f"\n{G}✔  Fast model:{RST} {W}{args[1]}{RST}")
        print(f"{DIM}Used for: casual chat, quick questions, simple lookups{RST}")
    elif sub == "smart" and len(args) > 1:
        set_key(env_path, "SMART_MODEL", args[1])
        print(f"\n{G}✔  Smart model:{RST} {W}{args[1]}{RST}")
        print(f"{DIM}Used for: code, research, analysis, long writing{RST}")
    elif sub == "off":
        set_key(env_path, "FAST_MODEL", "")
        print(f"\n{G}✔  Routing disabled{RST} — using single model for all tasks")
    else:
        print(f"\n{R}Usage: ninoclaw route fast|smart <model> | off{RST}\n")
        return
    print(f"{DIM}Restart the bot: ninoclaw start{RST}\n")



def cmd_think(args):
    """Toggle Ollama thinking mode on/off"""
    from dotenv import dotenv_values, set_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env = dotenv_values(env_path)
    current = env.get("OLLAMA_THINK", "false").lower() == "true"

    if not args:
        state = f"{G}ON{RST}" if current else f"{R}OFF{RST}"
        print(f"\n{C}🧠 Ollama thinking mode:{RST} {state}")
        print(f"{DIM}Usage: ninoclaw think on|off{RST}\n")
        return

    val = args[0].lower()
    if val in ("on", "true", "1", "yes"):
        set_key(env_path, "OLLAMA_THINK", "true")
        print(f"\n{G}✔  Thinking mode ON{RST} — Qwen3 will reason before answering")
    elif val in ("off", "false", "0", "no"):
        set_key(env_path, "OLLAMA_THINK", "false")
        print(f"\n{G}✔  Thinking mode OFF{RST} — faster responses")
    else:
        print(f"\n{R}Usage: ninoclaw think on|off{RST}\n")
        return
    print(f"{DIM}Restart the bot for changes to take effect: ninoclaw start{RST}\n")


def cmd_integrations(args):
    """Manage third-party integration credentials"""
    from dotenv import dotenv_values, set_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env = dotenv_values(env_path) if os.path.exists(env_path) else {}

    def clean_value(val):
        """Strip quotes from values to prevent credential issues"""
        val = val.strip()
        # Remove both single and double quotes from start/end
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        elif val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        return val

    INTEGRATION_VARS = [
        ("SLACK_WEBHOOK_URL",       "Slack Webhook"),
        ("SLACK_BOT_TOKEN",         "Slack Bot Token"),
        ("SLACK_CHANNEL",           "Slack Channel"),
        ("GITHUB_TOKEN",            "GitHub Token"),
        ("SPOTIFY_CLIENT_ID",       "Spotify Client ID"),
        ("SPOTIFY_CLIENT_SECRET",   "Spotify Client Secret"),
        ("SPOTIFY_REFRESH_TOKEN",   "Spotify Refresh Token"),
        ("LINKEDIN_ACCESS_TOKEN",   "LinkedIn Access Token"),
        ("GOOGLE_CREDENTIALS_JSON", "Google Credentials JSON"),
        ("GOOGLE_CALENDAR_ID",      "Google Calendar ID"),
    ]

    if not args:
        # Show all integrations with key status
        print(f"\n{C}🔌 Integrations{RST}")
        print(f"  {DIM}{'─'*44}{RST}")
        # Loaded skills
        try:
            import skill_manager
            skills = skill_manager.list_skills()
            if skills:
                for key, info in skills.items():
                    icon = info.get("icon", "🔧")
                    name = info.get("name", key)
                    req  = info.get("requires_key", False)
                    tag  = f"{Y}key required{RST}" if req else f"{G}active{RST}"
                    print(f"  {icon} {W}{name:<28}{RST} {tag}")
            else:
                print(f"  {DIM}No skills loaded.{RST}")
        except Exception as e:
            print(f"  {DIM}Could not load skills: {e}{RST}")
        print(f"\n  {DIM}{'─'*44}{RST}")
        # Env var status
        for var, label in INTEGRATION_VARS:
            val = env.get(var, "")
            if val:
                display = f"{val[:6]}...{val[-4:]}" if len(val) > 12 else val
                status  = f"{G}✔  {display}{RST}"
            else:
                status = f"{R}✗  Not set{RST}"
            print(f"  {W}{label:<28}{RST} {status}")
        print()
        return

    sub = args[0].lower()

    if sub == "slack" and len(args) >= 2:
        set_key(env_path, "SLACK_WEBHOOK_URL", clean_value(args[1]))
        print(f"\n{G}✔  SLACK_WEBHOOK_URL saved.{RST}{DIM}  Restart: ninoclaw start{RST}\n")

    elif sub == "github" and len(args) >= 2:
        set_key(env_path, "GITHUB_TOKEN", clean_value(args[1]))
        print(f"\n{G}✔  GITHUB_TOKEN saved.{RST}{DIM}  Restart: ninoclaw start{RST}\n")

    elif sub == "spotify" and len(args) >= 4:
        # Strip quotes from values to prevent credential issues
        def clean_value(val):
            val = val.strip()
            # Remove both single and double quotes from start/end
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            elif val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            return val

        set_key(env_path, "SPOTIFY_CLIENT_ID",     clean_value(args[1]))
        set_key(env_path, "SPOTIFY_CLIENT_SECRET", clean_value(args[2]))
        set_key(env_path, "SPOTIFY_REFRESH_TOKEN", clean_value(args[3]))
        print(f"\n{G}✔  Spotify credentials saved.{RST}{DIM}  Restart: ninoclaw start{RST}\n")

    elif sub == "spotify-setup" and len(args) >= 3:
        client_id, client_secret = args[1], args[2]
        import urllib.parse, requests as _req, base64 as _b64

        redirect_uri = "https://google.com"
        scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
        auth_url = (
            "https://accounts.spotify.com/authorize?"
            + urllib.parse.urlencode({
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": scope,
            })
        )

        print(f"\n{C}🎵 Spotify OAuth Setup{RST}")
        print(f"\n{W}1. Open this URL in Chrome:{RST}\n")
        print(f"   {B}{auth_url}{RST}\n")
        print(f"{W}2. Click Allow on the Spotify page")
        print(f"3. Chrome goes to google.com — copy the FULL URL from Chrome address bar")
        print(f"   It looks like: https://www.google.com/?code=AQBxyz...{RST}\n")
        raw = input(f"{W}4. Paste that full URL here:{RST} ").strip()
        if not raw:
            print(f"{R}Nothing entered.{RST}")
            return
        parsed = urllib.parse.urlparse(raw)
        code = urllib.parse.parse_qs(parsed.query).get("code", [""])[0]
        if not code:
            print(f"{R}❌ Could not find code in URL. Make sure you copied the full URL.{RST}")
            return

        creds_b64 = _b64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        resp = _req.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
            headers={"Authorization": f"Basic {creds_b64}"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"{R}❌ Token exchange failed: {resp.text}{RST}")
            return
        refresh_token = resp.json().get("refresh_token", "")
        if not refresh_token:
            print(f"{R}❌ No refresh token returned.{RST}")
            return
        # Strip quotes from values to prevent credential issues
        def clean_value(val):
            val = val.strip()
            # Remove both single and double quotes from start/end
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            elif val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            return val

        set_key(env_path, "SPOTIFY_CLIENT_ID",     clean_value(client_id))
        set_key(env_path, "SPOTIFY_CLIENT_SECRET", clean_value(client_secret))
        set_key(env_path, "SPOTIFY_REFRESH_TOKEN", clean_value(refresh_token))
        print(f"\n{G}✔  Spotify connected!{RST} Refresh token saved.")
        print(f"{DIM}Restart: ninoclaw start{RST}\n")

    elif sub == "gcal" and len(args) >= 2:
        set_key(env_path, "GOOGLE_CREDENTIALS_JSON", clean_value(args[1]))
        print(f"\n{G}✔  GOOGLE_CREDENTIALS_JSON saved.{RST}{DIM}  Restart: ninoclaw start{RST}\n")

    elif sub == "linkedin" and len(args) >= 2:
        set_key(env_path, "LINKEDIN_ACCESS_TOKEN", clean_value(args[1]))
        print(f"\n{G}✔  LINKEDIN_ACCESS_TOKEN saved.{RST}{DIM}  Restart: ninoclaw start{RST}\n")

    else:
        print(f"\n{W}Usage:{RST}")
        print(f"  {G}ninoclaw integrations{RST}                            List all")
        print(f"  {G}ninoclaw integrations slack{RST} <webhook_url>        Save webhook")
        print(f"  {G}ninoclaw integrations github{RST} <token>             Save token")
        print(f"  {G}ninoclaw integrations spotify{RST} <id> <secret> <rt> Save credentials")
        print(f"  {G}ninoclaw integrations gcal{RST} <path/to/creds.json>  Save creds path")
        print(f"  {G}ninoclaw integrations linkedin{RST} <access_token>      Save LinkedIn token\n")


def main():
    args = sys.argv[1:]
    cmd  = args[0].lower() if args else "start"

    if cmd in ("start", "run"):
        cmd_start()
    elif cmd in ("setup", "onboard", "configure", "config"):
        cmd_setup()
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "status":
        cmd_status()
    elif cmd == "memory":
        cmd_memory(args[1:])
    elif cmd == "update":
        cmd_update()
    elif cmd == "dashboard":
        cmd_dashboard()
    elif cmd == "model":
        cmd_model(args[1:])
    elif cmd == "think":
        cmd_think(args[1:])
    elif cmd == "route":
        cmd_route(args[1:])
    elif cmd in ("imagegen", "image"):
        cmd_imagegen(args[1:])
    elif cmd == "audit":
        from security_audit import security_auditor
        print(security_auditor.run_now())
    elif cmd == "integrations":
        cmd_integrations(args[1:])
    elif cmd == "version":
        cmd_version()
    elif cmd in ("help", "--help", "-h"):
        print(HELP)
    else:
        print(f"\n  {R}Unknown command:{RST} {cmd}")
        print(HELP)
        sys.exit(1)


if __name__ == "__main__":
    main()
