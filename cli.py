"""
Ninoclaw CLI — command line interface for managing the assistant
"""
import os
import sys

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
  {G}think{RST}              Toggle Ollama thinking mode (Qwen3 only)
    {DIM}ninoclaw think{RST}          Show current state
    {DIM}ninoclaw think on|off{RST}   Enable/disable thinking
  {G}version{RST}            Show current version (git commit)

{W}Examples:{RST}
  {DIM}ninoclaw{RST}                    Start the bot
  {DIM}ninoclaw setup{RST}              Configure API keys, model, etc.
  {DIM}ninoclaw reset{RST}              Wipe config and start fresh
  {DIM}ninoclaw status{RST}             Check what's configured
  {DIM}ninoclaw memory clear{RST}       Clear all conversations
  {DIM}ninoclaw memory stats{RST}       Show how much is stored
"""


def cmd_start():
    """Start the Ninoclaw bot"""
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
