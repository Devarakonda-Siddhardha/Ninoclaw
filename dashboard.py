"""
Ninoclaw Web Dashboard — configure plugins, view memory, manage tasks
Run with: ninoclaw dashboard  (or python dashboard.py)
"""
import os, sys, json, sqlite3, subprocess
from functools import wraps
from dotenv import load_dotenv, set_key, dotenv_values

# Lazy Flask import so the rest of the app doesn't depend on it
try:
    from flask import (Flask, render_template_string, request, redirect,
                       url_for, session, jsonify, flash)
except ImportError:
    print("Flask not installed. Run: pip install flask")
    sys.exit(1)

ENV_FILE  = os.path.join(os.path.dirname(__file__), ".env")
DB_FILE   = os.path.join(os.path.dirname(__file__), "ninoclaw.db")
DIR       = os.path.dirname(__file__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ─── helpers ────────────────────────────────────────────────────────────────

def get_env():
    return dotenv_values(ENV_FILE)

def save_env_key(key, value):
    set_key(ENV_FILE, key, value)

def get_db():
    if not os.path.exists(DB_FILE):
        return None
    return sqlite3.connect(DB_FILE)

def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def git_version():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=DIR).stdout.strip()
    except Exception:
        return "unknown"

# ─── base template ──────────────────────────────────────────────────────────

BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ninoclaw Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --surface2: #21262d;
    --border: #30363d; --accent: #58a6ff; --green: #3fb950;
    --red: #f85149; --yellow: #d29922; --text: #e6edf3; --muted: #8b949e;
  }
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; }
  .sidebar {
    width: 220px; min-height: 100vh; background: var(--surface);
    border-right: 1px solid var(--border); position: fixed; top: 0; left: 0;
    display: flex; flex-direction: column; padding: 0;
  }
  .sidebar-brand {
    padding: 20px 16px 16px; border-bottom: 1px solid var(--border);
    font-size: 1.1rem; font-weight: 700; color: var(--accent);
  }
  .sidebar-brand span { color: var(--muted); font-weight: 400; font-size: 0.75rem; display: block; margin-top: 2px; }
  .nav-link {
    display: flex; align-items: center; gap: 10px; padding: 10px 16px;
    color: var(--muted); text-decoration: none; font-size: 0.9rem;
    border-left: 3px solid transparent; transition: all 0.15s;
  }
  .nav-link:hover, .nav-link.active { color: var(--text); background: var(--surface2); border-left-color: var(--accent); }
  .nav-link i { font-size: 1rem; width: 18px; text-align: center; }
  .nav-section { padding: 14px 16px 4px; font-size: 0.7rem; text-transform: uppercase; color: var(--muted); letter-spacing: 0.08em; }
  .main { margin-left: 220px; padding: 28px 32px; min-height: 100vh; }
  .page-title { font-size: 1.4rem; font-weight: 600; margin-bottom: 6px; }
  .page-sub { color: var(--muted); font-size: 0.9rem; margin-bottom: 28px; }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; margin-bottom: 20px;
  }
  .card-header {
    padding: 14px 20px; border-bottom: 1px solid var(--border);
    font-weight: 600; font-size: 0.95rem; display: flex; align-items: center; gap: 8px;
  }
  .card-body { padding: 20px; }
  .form-label { color: var(--muted); font-size: 0.82rem; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
  .form-control, .form-select {
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; width: 100%;
  }
  .form-control:focus, .form-select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(88,166,255,0.15); background: var(--bg); color: var(--text); }
  .form-control::placeholder { color: var(--muted); }
  .btn { border-radius: 6px; padding: 8px 16px; font-size: 0.88rem; font-weight: 500; border: none; cursor: pointer; transition: opacity 0.15s; }
  .btn:hover { opacity: 0.85; }
  .btn-primary { background: var(--accent); color: #000; }
  .btn-danger  { background: var(--red); color: #fff; }
  .btn-success { background: var(--green); color: #000; }
  .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .badge-on  { background: var(--green); color: #000; border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-weight: 600; }
  .badge-off { background: var(--surface2); color: var(--muted); border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; text-align: center; }
  .stat-num { font-size: 2rem; font-weight: 700; color: var(--accent); }
  .stat-label { color: var(--muted); font-size: 0.82rem; margin-top: 4px; }
  .toggle-wrap { display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--border); }
  .toggle-wrap:last-child { border-bottom: none; }
  .toggle-info strong { display: block; font-size: 0.9rem; }
  .toggle-info small { color: var(--muted); font-size: 0.82rem; }
  .form-switch .form-check-input { width: 44px; height: 24px; cursor: pointer; background-color: var(--surface2); border-color: var(--border); }
  .form-switch .form-check-input:checked { background-color: var(--green); border-color: var(--green); }
  .alert { border-radius: 6px; padding: 10px 16px; margin-bottom: 16px; font-size: 0.88rem; }
  .alert-success { background: rgba(63,185,80,0.1); border: 1px solid rgba(63,185,80,0.3); color: var(--green); }
  .alert-danger   { background: rgba(248,81,73,0.1);  border: 1px solid rgba(248,81,73,0.3);  color: var(--red); }
  .table { color: var(--text); font-size: 0.88rem; }
  .table th { color: var(--muted); font-weight: 500; border-color: var(--border); padding: 8px 12px; }
  .table td { border-color: var(--border); padding: 8px 12px; vertical-align: middle; }
  .table-hover tbody tr:hover { background: var(--surface2); }
  .version-tag { background: var(--surface2); color: var(--muted); border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; font-family: monospace; }
  .key-masked { font-family: monospace; color: var(--muted); font-size: 0.85rem; }
  input[type=password] { letter-spacing: 0.1em; }
  .row { display: flex; flex-wrap: wrap; gap: 16px; margin: 0 0 20px 0; }
  .col { flex: 1; min-width: 140px; }
  @media (max-width: 768px) {
    .sidebar { transform: translateX(-100%); transition: transform 0.25s ease; z-index: 1000; }
    .sidebar.open { transform: translateX(0); }
    .overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999; }
    .overlay.open { display: block; }
    .main { margin-left: 0; padding: 12px; }
    .topbar { display: flex !important; }
    .stat-num { font-size: 1.5rem; }
    .table-wrap { overflow-x: auto; }
    .page-title { font-size: 1.15rem; }
  }
  .topbar {
    display: none; position: sticky; top: 0; z-index: 998;
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 10px 16px; align-items: center; gap: 12px;
    margin: -12px -12px 16px -12px;
  }
  .topbar-brand { font-weight: 700; color: var(--accent); font-size: 1rem; flex: 1; }
  .hamburger { background: none; border: none; color: var(--text); font-size: 1.4rem; cursor: pointer; padding: 0; line-height: 1; }
</style>
</head>
<body>
<div class="sidebar" id="sidebar">
  <div class="sidebar-brand">
    🦀 Ninoclaw
    <span>Dashboard <span class="version-tag">{{ version }}</span></span>
  </div>
  <nav style="flex:1; padding-top: 8px;">
    <div class="nav-section">Overview</div>
    <a href="{{ url_for('index') }}" class="nav-link {{ 'active' if active=='home' }}">
      <i class="bi bi-grid-1x2"></i> Overview
    </a>
    <div class="nav-section">Configuration</div>
    <a href="{{ url_for('config_page') }}" class="nav-link {{ 'active' if active=='config' }}">
      <i class="bi bi-gear"></i> Bot Config
    </a>
    <a href="{{ url_for('plugins_page') }}" class="nav-link {{ 'active' if active=='plugins' }}">
      <i class="bi bi-puzzle"></i> Plugins & Skills
    </a>
    <a href="{{ url_for('models_page') }}" class="nav-link {{ 'active' if active=='models' }}">
      <i class="bi bi-cpu"></i> AI Models
    </a>
    <div class="nav-section">Data</div>
    <a href="{{ url_for('memory_page') }}" class="nav-link {{ 'active' if active=='memory' }}">
      <i class="bi bi-people"></i> Memory
    </a>
    <a href="{{ url_for('chat_page') }}" class="nav-link {{ 'active' if active=='chat' }}">
      <i class="bi bi-chat-dots"></i> Chat History
    </a>
    <a href="{{ url_for('tasks_page') }}" class="nav-link {{ 'active' if active=='tasks' }}">
      <i class="bi bi-calendar-check"></i> Tasks & Crons
    </a>
  </nav>
  <div style="padding: 12px 16px; border-top: 1px solid var(--border);">
    <a href="{{ url_for('logout') }}" class="nav-link" style="padding: 8px 0;">
      <i class="bi bi-box-arrow-left"></i> Logout
    </a>
  </div>
</div>
<div class="overlay" id="overlay" onclick="closeNav()"></div>
<div class="main">
<div class="topbar">
  <button class="hamburger" onclick="openNav()">&#9776;</button>
  <span class="topbar-brand">🦀 Ninoclaw</span>
</div>
  {% for msg in get_flashed_messages(category_filter=['success']) %}
  <div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>{{ msg }}</div>
  {% endfor %}
  {% for msg in get_flashed_messages(category_filter=['error']) %}
  <div class="alert alert-danger"><i class="bi bi-x-circle me-2"></i>{{ msg }}</div>
  {% endfor %}


"""

FOOTER = """
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
function openNav()  { document.getElementById('sidebar').classList.add('open'); document.getElementById('overlay').classList.add('open'); }
function closeNav() { document.getElementById('sidebar').classList.remove('open'); document.getElementById('overlay').classList.remove('open'); }
</script>
</body>
</html>
"""

LOGIN_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ninoclaw — Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { background:#0d1117; color:#e6edf3; display:flex; align-items:center; justify-content:center; min-height:100vh; }
  .login-box { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:40px 36px; width:100%; max-width:380px; }
  .login-box h1 { font-size:1.5rem; font-weight:700; color:#58a6ff; margin-bottom:6px; }
  .login-box p { color:#8b949e; font-size:0.88rem; margin-bottom:28px; }
  label { color:#8b949e; font-size:0.8rem; text-transform:uppercase; letter-spacing:.04em; }
  input { background:#0d1117; border:1px solid #30363d; color:#e6edf3; border-radius:6px; padding:10px 14px; width:100%; margin-top:4px; font-size:0.92rem; outline:none; }
  input:focus { border-color:#58a6ff; box-shadow:0 0 0 3px rgba(88,166,255,.15); }
  button { background:#58a6ff; color:#000; border:none; border-radius:6px; padding:10px; width:100%; font-weight:600; margin-top:16px; cursor:pointer; font-size:0.95rem; }
  .err { background:rgba(248,81,73,.1); border:1px solid rgba(248,81,73,.3); color:#f85149; border-radius:6px; padding:8px 14px; margin-bottom:14px; font-size:.85rem; }
</style>
</head>
<body>
<div class="login-box">
  <h1>🦀 Ninoclaw</h1>
  <p>Sign in to the dashboard</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <label>Password</label>
    <input type="password" name="password" placeholder="Dashboard password" autofocus>
    <button type="submit">Sign In</button>
  </form>
</div>
</body>
</html>
"""

# ─── routes ─────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    from security import check_login_rate, reset_login_rate
    error = None
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        rate_err = check_login_rate(ip)
        if rate_err:
            error = rate_err
        else:
            env = get_env()
            pwd = env.get("DASHBOARD_PASSWORD", "admin")
            if request.form.get("password") == pwd:
                session["logged_in"] = True
                reset_login_rate(ip)
                return redirect(url_for("index"))
            error = "Incorrect password"
    return render_template_string(LOGIN_TMPL, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@require_login
def index():
    return redirect(url_for("chat_page"))


@app.route("/config", methods=["GET", "POST"])
@require_login
def config_page():
    env = get_env()
    if request.method == "POST":
        fields = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "OPENAI_API_URL",
                  "OPENAI_MODEL", "SERPER_API_KEY", "OWNER_ID",
                  "CONTEXT_WINDOW", "DASHBOARD_PASSWORD", "DASHBOARD_PORT",
                  "AGENT_NAME", "USER_NAME", "BOT_PURPOSE", "TIMEZONE",
                  "RESEND_API_KEY", "RESEND_FROM", "OWNER_EMAIL",
                  "OPENROUTER_API_KEY", "OPENROUTER_MODEL"]
        for f in fields:
            val = request.form.get(f, "").strip()
            if val:
                save_env_key(f, val)
        flash("Configuration saved!", "success")
        return redirect(url_for("config_page"))

    tmpl = BASE + """

<div class="page-title">Bot Configuration</div>
<div class="page-sub">Edit API keys and core settings. Saved directly to your .env file.</div>
<form method="POST">
<div class="card">
  <div class="card-header"><i class="bi bi-telegram"></i> Telegram</div>
  <div class="card-body">
    <div style="margin-bottom:16px">
      <label class="form-label">Bot Token</label>
      <input class="form-control" type="password" name="TELEGRAM_BOT_TOKEN" placeholder="Leave blank to keep current" autocomplete="off">
      {% if env.get('TELEGRAM_BOT_TOKEN') %}<small style="color:var(--muted)">Currently set: {{ env['TELEGRAM_BOT_TOKEN'][:10] }}...</small>{% endif %}
    </div>
    <div>
      <label class="form-label">Owner Telegram User ID</label>
      <input class="form-control" name="OWNER_ID" value="{{ env.get('OWNER_ID','') }}" placeholder="0 = disabled">
      <small style="color:var(--muted)">Get yours from @userinfobot on Telegram</small>
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-cpu"></i> Primary AI Model</div>
  <div class="card-body">
    <div style="margin-bottom:16px">
      <label class="form-label">API Key</label>
      <input class="form-control" type="password" name="OPENAI_API_KEY" placeholder="Leave blank to keep current" autocomplete="off">
      {% if env.get('OPENAI_API_KEY') %}<small style="color:var(--muted)">Currently set: {{ env['OPENAI_API_KEY'][:8] }}...</small>{% endif %}
    </div>
    <div style="margin-bottom:16px">
      <label class="form-label">API URL</label>
      <input class="form-control" name="OPENAI_API_URL" value="{{ env.get('OPENAI_API_URL','https://generativelanguage.googleapis.com/v1beta/openai') }}">
    </div>
    <div>
      <label class="form-label">Model Name</label>
      <input class="form-control" name="OPENAI_MODEL" value="{{ env.get('OPENAI_MODEL','gemini-2.0-flash-exp') }}">
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-search"></i> Web Search (Serper)</div>
  <div class="card-body">
    <div>
      <label class="form-label">Serper API Key</label>
      <input class="form-control" type="password" name="SERPER_API_KEY" placeholder="Leave blank to keep current" autocomplete="off">
      {% if env.get('SERPER_API_KEY') %}<small style="color:var(--muted)">Currently set: {{ env['SERPER_API_KEY'][:8] }}...</small>
      {% else %}<small style="color:var(--muted)">Get a free key at <a href="https://serper.dev" style="color:var(--accent)">serper.dev</a> (2500 free searches/month)</small>{% endif %}
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-envelope"></i> Resend Email  <small style="color:var(--muted);font-weight:400">(skill: resend_email)</small></div>
  <div class="card-body">
    <div style="margin-bottom:16px">
      <label class="form-label">Resend API Key</label>
      <input class="form-control" type="password" name="RESEND_API_KEY" placeholder="re_xxxx... — leave blank to keep current" autocomplete="off">
      {% if env.get('RESEND_API_KEY') %}<small style="color:var(--green)">✓ Set</small>
      {% else %}<small style="color:var(--muted)">Free at <a href="https://resend.com" style="color:var(--accent)">resend.com</a> — 100 emails/day</small>{% endif %}
    </div>
    <div style="margin-bottom:16px">
      <label class="form-label">From Address  <small>(verified sender in Resend)</small></label>
      <input class="form-control" name="RESEND_FROM" value="{{ env.get('RESEND_FROM','') }}" placeholder="you@yourdomain.com">
    </div>
    <div>
      <label class="form-label">Your Email  <small>(default recipient)</small></label>
      <input class="form-control" name="OWNER_EMAIL" value="{{ env.get('OWNER_EMAIL','') }}" placeholder="you@gmail.com">
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-person-circle"></i> Personalization</div>
  <div class="card-body">
    <div style="margin-bottom:16px">
      <label class="form-label">Bot Name</label>
      <input class="form-control" name="AGENT_NAME" value="{{ env.get('AGENT_NAME','Ninoclaw') }}">
    </div>
    <div style="margin-bottom:16px">
      <label class="form-label">Your Name</label>
      <input class="form-control" name="USER_NAME" value="{{ env.get('USER_NAME','friend') }}">
    </div>
    <div style="margin-bottom:16px">
      <label class="form-label">Bot Purpose</label>
      <input class="form-control" name="BOT_PURPOSE" value="{{ env.get('BOT_PURPOSE','be your personal AI assistant') }}">
    </div>
    <div>
      <label class="form-label">Timezone</label>
      <input class="form-control" name="TIMEZONE" value="{{ env.get('TIMEZONE','UTC') }}" placeholder="Asia/Kolkata">
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-diagram-3"></i> OpenRouter  <small style="color:var(--muted);font-weight:400">100+ models in one API — <a href="https://openrouter.ai/keys" style="color:var(--accent)">openrouter.ai</a></small></div>
  <div class="card-body">
    <div style="margin-bottom:14px">
      <label class="form-label">OpenRouter API Key</label>
      <input class="form-control" type="password" name="OPENROUTER_API_KEY" placeholder="sk-or-... — leave blank to keep current" autocomplete="off">
      {% if env.get('OPENROUTER_API_KEY') %}<small style="color:var(--green)">✓ Set — used as fallback automatically</small>
      {% else %}<small style="color:var(--muted)">Free credits on signup. Use any model like <code>google/gemini-flash-1.5</code></small>{% endif %}
    </div>
    <div>
      <label class="form-label">OpenRouter Model  <small>(when used as primary)</small></label>
      <input class="form-control" name="OPENROUTER_MODEL" value="{{ env.get('OPENROUTER_MODEL','google/gemini-flash-1.5') }}">
    </div>
  </div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-sliders"></i> Advanced</div>
  <div class="card-body">
    <div style="margin-bottom:16px">
      <label class="form-label">Context Window (messages sent to AI per request)</label>
      <input class="form-control" name="CONTEXT_WINDOW" value="{{ env.get('CONTEXT_WINDOW','20') }}" style="max-width:120px">
    </div>
    <div style="margin-bottom:16px">
      <label class="form-label">Dashboard Password</label>
      <input class="form-control" type="password" name="DASHBOARD_PASSWORD" placeholder="Leave blank to keep current" autocomplete="off">
    </div>
    <div>
      <label class="form-label">Dashboard Port</label>
      <input class="form-control" name="DASHBOARD_PORT" value="{{ env.get('DASHBOARD_PORT','8080') }}" style="max-width:120px">
    </div>
  </div>
</div>
<button type="submit" class="btn btn-primary"><i class="bi bi-save me-1"></i> Save Configuration</button>
</form>

"""
    return render_template_string(tmpl + FOOTER, active="config", version=git_version(), env=env)


@app.route("/plugins", methods=["GET", "POST"])
@require_login
def plugins_page():
    env = get_env()
    if request.method == "POST":
        # Built-in plugin flags
        plugins = {
            "ENABLE_WEB_SEARCH": request.form.get("ENABLE_WEB_SEARCH", "false"),
            "ENABLE_VISION":     request.form.get("ENABLE_VISION", "false"),
            "ENABLE_SUMMARIZER": request.form.get("ENABLE_SUMMARIZER", "false"),
            "ENABLE_REMINDERS":  request.form.get("ENABLE_REMINDERS", "false"),
            "ENABLE_CRON":       request.form.get("ENABLE_CRON", "false"),
            "ENABLE_SELF_UPDATE":request.form.get("ENABLE_SELF_UPDATE", "false"),
        }
        for k, v in plugins.items():
            save_env_key(k, v)
        # Skills: build DISABLED_SKILLS list from unchecked boxes
        try:
            import skill_manager as sm
            all_skills = sm.list_all_skill_files()
            disabled = [s for s in all_skills if request.form.get(f"SKILL_{s}") != "true"]
            save_env_key("DISABLED_SKILLS", ",".join(disabled))
        except Exception:
            pass
        flash("Settings saved! Restart bot to apply.", "success")
        return redirect(url_for("plugins_page"))

    def is_on(key, default="true"):
        return env.get(key, default) != "false"

    # Load skills info
    skills_data = []
    try:
        import skill_manager as sm
        all_skill_files = sm.list_all_skill_files()
        disabled_skills = {s.strip() for s in env.get("DISABLED_SKILLS","").split(",") if s.strip()}
        loaded = sm.list_skills()
        sys.path.insert(0, DIR)
        import importlib
        for sk in all_skill_files:
            try:
                mod = importlib.import_module(f"skills.{sk}")
                info = getattr(mod, "SKILL_INFO", {"name": sk, "description": "", "icon": "🔧"})
                tools_count = len(getattr(mod, "TOOLS", []))
                skills_data.append({
                    "key": sk, "info": info,
                    "enabled": sk not in disabled_skills,
                    "tools": tools_count
                })
            except Exception:
                skills_data.append({"key": sk, "info": {"name": sk, "description": "Failed to load", "icon": "⚠️"}, "enabled": False, "tools": 0})
    except Exception:
        pass

    tmpl = BASE + """

<div class="page-title">Plugins & Skills</div>
<div class="page-sub">Toggle built-in features and skills. Restart bot to apply changes.</div>
<form method="POST">

<div class="card">
  <div class="card-header"><i class="bi bi-puzzle"></i> Built-in Plugins</div>
  <div class="card-body" style="padding: 8px 20px;">

    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong><i class="bi bi-search me-2" style="color:var(--accent)"></i>Web Search</strong>
        <small>Search Google for real-time info, news, scores, prices. Requires Serper API key.</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="ENABLE_WEB_SEARCH" value="true" {{ 'checked' if web_search }}>
      </div>
    </div>

    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong><i class="bi bi-eye me-2" style="color:#a371f7"></i>Image Vision</strong>
        <small>Analyze photos sent to the bot. Uses the AI's multimodal capabilities.</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="ENABLE_VISION" value="true" {{ 'checked' if vision }}>
      </div>
    </div>

    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong><i class="bi bi-link-45deg me-2" style="color:#f78166"></i>URL Summarizer</strong>
        <small>Automatically summarize YouTube videos and web pages when a URL is sent.</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="ENABLE_SUMMARIZER" value="true" {{ 'checked' if summarizer }}>
      </div>
    </div>

    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong><i class="bi bi-bell me-2" style="color:var(--yellow)"></i>Reminders</strong>
        <small>One-time reminders — "remind me in 30 minutes to call mom".</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="ENABLE_REMINDERS" value="true" {{ 'checked' if reminders }}>
      </div>
    </div>

    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong><i class="bi bi-clock-history me-2" style="color:var(--green)"></i>Cron Scheduler</strong>
        <small>Recurring tasks — "every day at 9am remind me to drink water".</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="ENABLE_CRON" value="true" {{ 'checked' if cron }}>
      </div>
    </div>

    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong><i class="bi bi-arrow-repeat me-2" style="color:var(--muted)"></i>Self Update</strong>
        <small>Allow the bot to update itself from GitHub when asked. Owner-locked.</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="ENABLE_SELF_UPDATE" value="true" {{ 'checked' if self_update }}>
      </div>
    </div>

  </div>
</div>

<div class="card">
  <div class="card-header">
    <i class="bi bi-stars"></i> Skills
    <span style="color:var(--muted);font-size:0.8rem;font-weight:400;margin-left:8px">
      {{ skills|length }} installed · drop a .py file in the <code>skills/</code> folder to add more
    </span>
  </div>
  <div class="card-body" style="padding: 8px 20px;">
  {% if skills %}
    {% for sk in skills %}
    <div class="toggle-wrap">
      <div class="toggle-info">
        <strong>{{ sk.info.get('icon','🔧') }} {{ sk.info.get('name', sk.key) }}
          <span style="color:var(--muted);font-size:0.75rem;font-weight:400">v{{ sk.info.get('version','1.0') }}</span>
          <span style="color:var(--muted);font-size:0.75rem;margin-left:6px">· {{ sk.tools }} tool{{ 's' if sk.tools != 1 else '' }}</span>
        </strong>
        <small>{{ sk.info.get('description','') }}</small>
      </div>
      <div class="form-check form-switch ms-3">
        <input class="form-check-input" type="checkbox" name="SKILL_{{ sk.key }}" value="true" {{ 'checked' if sk.enabled }}>
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div style="color:var(--muted);padding:16px 0;font-size:0.9rem">No skills found in <code>skills/</code> folder.</div>
  {% endif %}
  </div>
</div>

<button type="submit" class="btn btn-primary"><i class="bi bi-save me-1"></i> Save All Settings</button>
<p style="color:var(--muted);font-size:0.8rem;margin-top:12px;">⚠ Run <code>ninoclaw restart</code> for changes to take effect.</p>
</form>

"""
    return render_template_string(tmpl + FOOTER, active="plugins", version=git_version(), env=env,
        skills=skills_data,
        web_search=is_on("ENABLE_WEB_SEARCH"),
        vision=is_on("ENABLE_VISION"),
        summarizer=is_on("ENABLE_SUMMARIZER"),
        reminders=is_on("ENABLE_REMINDERS"),
        cron=is_on("ENABLE_CRON"),
        self_update=is_on("ENABLE_SELF_UPDATE"))


@app.route("/models", methods=["GET", "POST"])
@require_login
def models_page():
    env = get_env()
    if request.method == "POST":
        section = request.form.get("section", "fallback")
        if section == "primary":
            model = request.form.get("OPENAI_MODEL", "").strip()
            url   = request.form.get("OPENAI_API_URL", "").strip()
            key   = request.form.get("OPENAI_API_KEY", "").strip()
            if model: save_env_key("OPENAI_MODEL", model)
            if url:   save_env_key("OPENAI_API_URL", url)
            if key:   save_env_key("OPENAI_API_KEY", key)
        else:
            fallback_model = request.form.get("FALLBACK_MODEL", "").strip()
            fallback_key   = request.form.get("FALLBACK_API_KEY", "").strip()
            fallback_url   = request.form.get("FALLBACK_API_URL", "").strip()
            if fallback_model: save_env_key("FALLBACK_MODEL", fallback_model)
            if fallback_key:   save_env_key("FALLBACK_API_KEY", fallback_key)
            if fallback_url:   save_env_key("FALLBACK_API_URL", fallback_url)
        flash("Model settings saved!", "success")
        return redirect(url_for("models_page"))

    tmpl = BASE + """

<div class="page-title">AI Models</div>
<div class="page-sub">Configure primary and fallback AI models. The bot tries each in order.</div>

<div class="card">
  <div class="card-header"><i class="bi bi-1-circle"></i> Primary Model</div>
  <div class="card-body">
    <form method="POST">
    <input type="hidden" name="section" value="primary">
    <div style="margin-bottom:14px">
      <label class="form-label">Model Name</label>
      <input class="form-control" name="OPENAI_MODEL" value="{{ env.get('OPENAI_MODEL','gemini-3-flash-preview') }}" placeholder="e.g. gemini-3-flash-preview">
    </div>
    <div style="margin-bottom:14px">
      <label class="form-label">API URL</label>
      <input class="form-control" name="OPENAI_API_URL" value="{{ env.get('OPENAI_API_URL','https://generativelanguage.googleapis.com/v1beta/openai') }}">
    </div>
    <div style="margin-bottom:14px">
      <label class="form-label">API Key</label>
      <input class="form-control" type="password" name="OPENAI_API_KEY" placeholder="Leave blank to keep current" autocomplete="off">
      {% if env.get('OPENAI_API_KEY') %}<small style="color:var(--green)">✓ Set</small>{% endif %}
    </div>
    <button type="submit" class="btn btn-primary"><i class="bi bi-save me-1"></i> Save Primary</button>
    </form>
  </div>
</div>

<div class="card">
  <div class="card-header"><i class="bi bi-2-circle"></i> Fallback Model</div>
  <div class="card-body">
    <p style="color:var(--muted);font-size:0.88rem">Used automatically if the primary model fails or is rate-limited.</p>
    <form method="POST">
    <input type="hidden" name="section" value="fallback">
    <div style="margin-bottom:14px">
      <input class="form-control" name="FALLBACK_MODEL" value="{{ env.get('FALLBACK_MODEL','') }}" placeholder="e.g. gemini-1.5-flash">
    </div>
    <div style="margin-bottom:14px">
      <label class="form-label">Fallback API Key (if different)</label>
      <input class="form-control" type="password" name="FALLBACK_API_KEY" placeholder="Leave blank to use primary key" autocomplete="off">
    </div>
    <div style="margin-bottom:14px">
      <label class="form-label">Fallback API URL (if different)</label>
      <input class="form-control" name="FALLBACK_API_URL" value="{{ env.get('FALLBACK_API_URL','') }}" placeholder="Leave blank to use primary URL">
    </div>
    <button type="submit" class="btn btn-primary"><i class="bi bi-save me-1"></i> Save</button>
    </form>
  </div>
</div>

<div class="card">
  <div class="card-header"><i class="bi bi-list-ol"></i> Suggested Models</div>
  <div class="card-body">
    <div class="table-wrap"><table class="table table-hover">
      <thead><tr><th>Model</th><th>Provider</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td><code>gemini-3-flash-preview</code></td><td>Google</td><td>Latest, fast</td></tr>
        <tr><td><code>gemini-2.5-flash-preview-04-17</code></td><td>Google</td><td>Stable preview</td></tr>
        <tr><td><code>gemini-2.0-flash-exp</code></td><td>Google</td><td>Free tier</td></tr>
        <tr><td><code>gpt-4o-mini</code></td><td>OpenAI</td><td>Affordable</td></tr>
        <tr><td><code>gpt-4o</code></td><td>OpenAI</td><td>Best quality</td></tr>
        <tr><td><code>mistral-small-latest</code></td><td>Mistral</td><td>Free tier</td></tr>
        <tr><td><code>google/gemini-flash-1.5</code></td><td>OpenRouter</td><td>Via openrouter.ai</td></tr>
        <tr><td><code>google/gemini-2.0-flash-exp:free</code></td><td>OpenRouter</td><td>Free on OpenRouter</td></tr>
        <tr><td><code>meta-llama/llama-3.3-70b-instruct:free</code></td><td>OpenRouter</td><td>Free Llama 3.3</td></tr>
        <tr><td><code>llama3.2</code></td><td>Ollama (local)</td><td>Offline, private</td></tr>
      </tbody>
    </table></div>
  </div>
</div>

"""
    return render_template_string(tmpl + FOOTER, active="models", version=git_version(), env=env)


@app.route("/memory")
@require_login
def memory_page():
    conn = get_db()
    users = []
    if conn:
        try:
            users = conn.execute(
                "SELECT user_id, COUNT(*) as cnt, MAX(ts) as last "
                "FROM conversations GROUP BY user_id ORDER BY cnt DESC"
            ).fetchall()
        except Exception:
            pass
        conn.close()

    tmpl = BASE + """

<div class="page-title">Memory</div>
<div class="page-sub">Conversation history stored in the local SQLite database.</div>

<div class="card">
  <div class="card-header"><i class="bi bi-people"></i> Users ({{ users|length }})</div>
  <div class="card-body" style="padding:0">
    {% if users %}
    <div class="table-wrap"><table class="table table-hover mb-0">
      <thead><tr><th>User ID</th><th>Messages</th><th>Last Active</th><th></th></tr></thead>
      <tbody>
      {% for uid, cnt, last in users %}
      <tr>
        <td><code>{{ uid }}</code></td>
        <td>{{ cnt }}</td>
        <td style="color:var(--muted);font-size:0.82rem">{{ last }}</td>
        <td style="display:flex;gap:6px">
          <a href="{{ url_for('chat_view', user_id=uid) }}" class="btn btn-outline" style="padding:4px 10px;font-size:0.8rem">
            <i class="bi bi-chat-text"></i> View
          </a>
          <form method="POST" action="/memory/clear" style="display:inline">
            <input type="hidden" name="user_id" value="{{ uid }}">
            <button type="submit" class="btn btn-danger" style="padding:4px 10px;font-size:0.8rem"
              onclick="return confirm('Clear memory for {{ uid }}?')">
              <i class="bi bi-trash"></i> Clear
            </button>
          </form>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table></div>
    {% else %}
    <div style="padding:24px;text-align:center;color:var(--muted)">No conversations yet</div>
    {% endif %}
  </div>
</div>

<form method="POST" action="/memory/clear" onsubmit="return confirm('Clear ALL memory for ALL users?')">
  <button type="submit" class="btn btn-danger"><i class="bi bi-trash me-1"></i> Clear All Memory</button>
</form>

"""
    return render_template_string(tmpl + FOOTER, active="memory", version=git_version(), users=users)


@app.route("/memory/clear", methods=["POST"])
@require_login
def memory_clear():
    conn = get_db()
    if conn:
        uid = request.form.get("user_id")
        if uid:
            conn.execute("DELETE FROM conversations WHERE user_id=?", (uid,))
        else:
            conn.execute("DELETE FROM conversations")
        conn.commit()
        conn.close()
    flash("Memory cleared.", "success")
    return redirect(url_for("memory_page"))


@app.route("/chat")
@require_login
def chat_page():
    """Chat history — pick a user"""
    conn = get_db()
    users = []
    if conn:
        try:
            users = conn.execute(
                "SELECT user_id, COUNT(*) as cnt, MAX(ts) as last "
                "FROM conversations GROUP BY user_id ORDER BY last DESC"
            ).fetchall()
        except Exception:
            pass
        conn.close()

    tmpl = BASE + """

<div class="page-title">Chat History</div>
<div class="page-sub">Live view of every conversation synced from the bot's memory.</div>
{% if users %}
<div class="card">
  <div class="card-header"><i class="bi bi-people"></i> Select a conversation</div>
  <div class="card-body" style="padding:0">
    <div class="table-wrap"><table class="table table-hover mb-0">
      <thead><tr><th>User ID</th><th>Messages</th><th>Last Active</th><th></th></tr></thead>
      <tbody>
      {% for uid, cnt, last in users %}
      <tr>
        <td><code>{{ uid }}</code></td>
        <td>{{ cnt }}</td>
        <td style="color:var(--muted);font-size:0.82rem">{{ last }}</td>
        <td><a href="{{ url_for('chat_view', user_id=uid) }}" class="btn btn-primary" style="padding:5px 14px;font-size:0.82rem">
          <i class="bi bi-chat-dots me-1"></i> Open Chat
        </a></td>
      </tr>
      {% endfor %}
      </tbody>
    </table></div>
  </div>
</div>
{% else %}
<div class="card"><div class="card-body" style="text-align:center;color:var(--muted);padding:40px">
  <i class="bi bi-chat-dots" style="font-size:2.5rem;display:block;margin-bottom:12px"></i>
  No conversations yet. Start chatting with your bot on Telegram!
</div></div>
{% endif %}

"""
    return render_template_string(tmpl + FOOTER, active="chat", version=git_version(), users=users)


@app.route("/api/chat/<user_id>/send", methods=["POST"])
@require_login
def chat_send(user_id):
    """Send a message as the user and get AI response"""
    data = request.get_json()
    text = (data or {}).get("message", "").strip()
    if not text:
        return jsonify({"error": "empty message"}), 400
    try:
        sys.path.insert(0, DIR)
        from memory import memory as mem
        from ai import chat as ai_chat
        mem.add_message(user_id, "user", text)
        context = mem.get_conversation_context(user_id)
        reply = ai_chat(context)
        # strip tool-call noise if any
        if isinstance(reply, dict):
            reply = reply.get("content", str(reply))
        mem.add_message(user_id, "assistant", reply)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat/<user_id>")
@require_login
def chat_view(user_id):
    """Full chat UI for a specific user"""
    conn = get_db()
    messages = []
    if conn:
        try:
            rows = conn.execute(
                "SELECT role, content, ts FROM conversations WHERE user_id=? ORDER BY id ASC",
                (user_id,)
            ).fetchall()
            messages = [{"role": r[0], "content": r[1], "ts": r[2]} for r in rows]
        except Exception:
            pass
        conn.close()

    # API endpoint for polling
    if request.args.get("format") == "json":
        return jsonify(messages)

    tmpl = BASE + """

<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
  <div>
    <div class="page-title" style="margin-bottom:2px">
      <a href="{{ url_for('chat_page') }}" style="color:var(--muted);text-decoration:none;font-size:1rem;margin-right:8px">
        <i class="bi bi-arrow-left"></i>
      </a>
      Chat — <code style="font-size:1.1rem;color:var(--accent)">{{ user_id }}</code>
    </div>
    <div class="page-sub" style="margin-bottom:0">{{ messages|length }} messages · auto-refreshes every 5s</div>
  </div>
  <div style="display:flex;gap:8px">
    <button onclick="scrollToBottom()" class="btn btn-outline" style="font-size:0.82rem">
      <i class="bi bi-arrow-down-circle"></i> Bottom
    </button>
    <form method="POST" action="/memory/clear" style="display:inline"
      onsubmit="return confirm('Clear all memory for this user?')">
      <input type="hidden" name="user_id" value="{{ user_id }}">
      <button type="submit" class="btn btn-danger" style="font-size:0.82rem">
        <i class="bi bi-trash"></i> Clear
      </button>
    </form>
  </div>
</div>

<div id="chat-wrap" style="
  background:var(--surface); border:1px solid var(--border); border-radius:8px 8px 0 0;
  height: calc(100vh - 260px); overflow-y:auto; padding:20px;
  display:flex; flex-direction:column; gap:12px;
">
  <div id="chat-messages">
  {% for msg in messages %}
    {% if msg.role == 'user' %}
    <div style="display:flex;justify-content:flex-end;">
      <div style="max-width:70%">
        <div style="
          background: #1c4a9c; color:#e6edf3; border-radius:18px 18px 4px 18px;
          padding:10px 16px; font-size:0.9rem; line-height:1.5; word-break:break-word;
        ">{{ msg.content }}</div>
        <div style="text-align:right;color:var(--muted);font-size:0.72rem;margin-top:3px;padding-right:4px">
          {{ msg.ts[:16] if msg.ts else '' }}
        </div>
      </div>
    </div>
    {% else %}
    <div style="display:flex;justify-content:flex-start;gap:8px;align-items:flex-end">
      <div style="
        width:32px;height:32px;border-radius:50%;background:var(--accent);
        display:flex;align-items:center;justify-content:center;
        font-size:0.9rem;flex-shrink:0;margin-bottom:18px
      ">🦀</div>
      <div style="max-width:70%">
        <div style="
          background:var(--surface2); color:var(--text); border-radius:18px 18px 18px 4px;
          padding:10px 16px; font-size:0.9rem; line-height:1.5; word-break:break-word;
          border:1px solid var(--border);
          white-space: pre-wrap;
        ">{{ msg.content }}</div>
        <div style="color:var(--muted);font-size:0.72rem;margin-top:3px;padding-left:4px">
          {{ msg.ts[:16] if msg.ts else '' }}
        </div>
      </div>
    </div>
    {% endif %}
  {% endfor %}
  {% if not messages %}
  <div style="text-align:center;color:var(--muted);margin:auto">No messages yet — say something below!</div>
  {% endif %}
  </div>
  <!-- typing indicator -->
  <div id="typing-indicator" style="display:none;gap:8px;align-items:flex-end">
    <div style="width:32px;height:32px;border-radius:50%;background:var(--accent);
      display:flex;align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0">🦀</div>
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:18px 18px 18px 4px;
      padding:10px 18px;display:flex;gap:5px;align-items:center">
      <span style="width:7px;height:7px;background:var(--muted);border-radius:50%;display:inline-block;animation:blink 1.2s infinite 0s"></span>
      <span style="width:7px;height:7px;background:var(--muted);border-radius:50%;display:inline-block;animation:blink 1.2s infinite 0.3s"></span>
      <span style="width:7px;height:7px;background:var(--muted);border-radius:50%;display:inline-block;animation:blink 1.2s infinite 0.6s"></span>
    </div>
  </div>
  <style>@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}</style>
  <div id="chat-bottom"></div>
</div>

<!-- Input bar -->
<div style="
  background:var(--surface); border:1px solid var(--border); border-top:none;
  border-radius:0 0 8px 8px; padding:12px 16px;
  display:flex; gap:10px; align-items:flex-end;
">
  <textarea id="msg-input" rows="1" placeholder="Type a message…" style="
    flex:1; background:var(--bg); border:1px solid var(--border); color:var(--text);
    border-radius:20px; padding:10px 16px; font-size:0.9rem; resize:none;
    outline:none; max-height:120px; line-height:1.4; font-family:inherit;
  " oninput="this.style.height='auto';this.style.height=this.scrollHeight+'px'"
    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"
  ></textarea>
  <button id="send-btn" onclick="sendMessage()" style="
    background:var(--accent); color:#000; border:none; border-radius:50%;
    width:42px; height:42px; display:flex; align-items:center; justify-content:center;
    font-size:1.1rem; cursor:pointer; flex-shrink:0; transition:opacity 0.15s;
  "><i class="bi bi-send-fill"></i></button>
</div>

<script>
const userId = {{ user_id|tojson }};
let lastCount = {{ messages|length }};
let autoScroll = true;
let sending = false;

const wrap = document.getElementById('chat-wrap');
wrap.addEventListener('scroll', () => {
  autoScroll = wrap.scrollTop + wrap.clientHeight >= wrap.scrollHeight - 60;
});

function scrollToBottom() {
  wrap.scrollTop = wrap.scrollHeight;
  autoScroll = true;
}

function nowTs() {
  return new Date().toISOString().slice(0,16).replace('T',' ');
}

function appendMsg(role, content, ts) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.innerHTML = renderMsg({role, content, ts: ts || nowTs()});
  container.appendChild(div.firstElementChild);
  lastCount++;
  if (autoScroll) scrollToBottom();
}

function setTyping(show) {
  const el = document.getElementById('typing-indicator');
  el.style.display = show ? 'flex' : 'none';
  if (show && autoScroll) scrollToBottom();
}

async function sendMessage() {
  if (sending) return;
  const input = document.getElementById('msg-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  input.style.height = 'auto';
  sending = true;
  document.getElementById('send-btn').style.opacity = '0.5';

  appendMsg('user', text, nowTs());
  setTyping(true);

  try {
    const res = await fetch(`/api/chat/${userId}/send`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    setTyping(false);
    if (data.reply) {
      appendMsg('assistant', data.reply, nowTs());
    } else {
      appendMsg('assistant', '⚠️ ' + (data.error || 'Unknown error'), nowTs());
    }
  } catch(e) {
    setTyping(false);
    appendMsg('assistant', '⚠️ Failed to reach server', nowTs());
  }

  sending = false;
  document.getElementById('send-btn').style.opacity = '1';
  input.focus();
}

function renderMsg(msg) {
  const ts = msg.ts ? msg.ts.slice(0,16) : '';
  if (msg.role === 'user') {
    return `<div style="display:flex;justify-content:flex-end;">
      <div style="max-width:70%">
        <div style="background:#1c4a9c;color:#e6edf3;border-radius:18px 18px 4px 18px;
          padding:10px 16px;font-size:0.9rem;line-height:1.5;word-break:break-word;">
          ${escHtml(msg.content)}</div>
        <div style="text-align:right;color:var(--muted);font-size:0.72rem;margin-top:3px;padding-right:4px">${ts}</div>
      </div></div>`;
  } else {
    return `<div style="display:flex;justify-content:flex-start;gap:8px;align-items:flex-end">
      <div style="width:32px;height:32px;border-radius:50%;background:var(--accent);
        display:flex;align-items:center;justify-content:center;font-size:0.9rem;
        flex-shrink:0;margin-bottom:18px">🦀</div>
      <div style="max-width:70%">
        <div style="background:var(--surface2);color:var(--text);border-radius:18px 18px 18px 4px;
          padding:10px 16px;font-size:0.9rem;line-height:1.5;word-break:break-word;
          border:1px solid var(--border);white-space:pre-wrap;">
          ${escHtml(msg.content)}</div>
        <div style="color:var(--muted);font-size:0.72rem;margin-top:3px;padding-left:4px">${ts}</div>
      </div></div>`;
  }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function pollMessages() {
  if (sending) return;
  try {
    const res = await fetch(`/chat/${userId}?format=json`);
    const msgs = await res.json();
    if (msgs.length > lastCount) {
      const container = document.getElementById('chat-messages');
      const newMsgs = msgs.slice(lastCount);
      newMsgs.forEach(m => {
        const div = document.createElement('div');
        div.innerHTML = renderMsg(m);
        container.appendChild(div.firstElementChild);
      });
      lastCount = msgs.length;
      if (autoScroll) scrollToBottom();
    }
  } catch(e) {}
}

scrollToBottom();
setInterval(pollMessages, 5000);
document.getElementById('msg-input').focus();
</script>

"""
    return render_template_string(tmpl + FOOTER, active="chat", version=git_version(),
                                  user_id=user_id, messages=messages)


@app.route("/tasks")
@require_login
def tasks_page():
    conn = get_db()
    tasks, crons = [], []
    if conn:
        try:
            tasks = conn.execute(
                "SELECT id, user_id, description, due_time, completed "
                "FROM tasks ORDER BY due_time ASC"
            ).fetchall()
            crons = conn.execute(
                "SELECT id, user_id, description, cron_expr, is_active "
                "FROM cron_jobs ORDER BY id DESC"
            ).fetchall()
        except Exception:
            pass
        conn.close()

    tmpl = BASE + """

<div class="page-title">Tasks & Cron Jobs</div>
<div class="page-sub">Reminders and recurring schedules across all users.</div>

<div class="card">
  <div class="card-header"><i class="bi bi-alarm"></i> Pending Reminders</div>
  <div class="card-body" style="padding:0">
    {% if tasks %}
    <div class="table-wrap"><table class="table table-hover mb-0">
      <thead><tr><th>User</th><th>Description</th><th>Due At</th><th>Status</th></tr></thead>
      <tbody>
      {% for tid, uid, desc, due, done in tasks %}
      <tr>
        <td><code>{{ uid }}</code></td>
        <td>{{ desc }}</td>
        <td style="font-size:0.82rem;color:var(--muted)">{{ due }}</td>
        <td>{% if done %}<span class="badge-on">Done</span>{% else %}<span style="color:var(--yellow)">⏳ Pending</span>{% endif %}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table></div>
    {% else %}
    <div style="padding:24px;text-align:center;color:var(--muted)">No reminders set</div>
    {% endif %}
  </div>
</div>

<div class="card">
  <div class="card-header"><i class="bi bi-clock-history"></i> Recurring Cron Jobs</div>
  <div class="card-body" style="padding:0">
    {% if crons %}
    <div class="table-wrap"><table class="table table-hover mb-0">
      <thead><tr><th>User</th><th>Description</th><th>Schedule</th><th>Status</th></tr></thead>
      <tbody>
      {% for cid, uid, desc, expr, active in crons %}
      <tr>
        <td><code>{{ uid }}</code></td>
        <td>{{ desc }}</td>
        <td><code style="color:var(--accent)">{{ expr }}</code></td>
        <td>{% if active %}<span class="badge-on">Active</span>{% else %}<span class="badge-off">Paused</span>{% endif %}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table></div>
    {% else %}
    <div style="padding:24px;text-align:center;color:var(--muted)">No cron jobs yet</div>
    {% endif %}
  </div>
</div>

"""
    return render_template_string(tmpl + FOOTER, active="tasks", version=git_version(),
                                  tasks=tasks, crons=crons)


# ─── entry point ────────────────────────────────────────────────────────────

def run_dashboard():
    load_dotenv(ENV_FILE)
    env = get_env()
    port = int(env.get("DASHBOARD_PORT", os.getenv("DASHBOARD_PORT", "8080")))
    host = "0.0.0.0"

    # Set a default password if none exists
    if not env.get("DASHBOARD_PASSWORD"):
        save_env_key("DASHBOARD_PASSWORD", "admin")

    print(f"\n🦀 Ninoclaw Dashboard")
    print(f"   URL:      http://localhost:{port}")
    print(f"   Password: {env.get('DASHBOARD_PASSWORD', 'admin')}")
    print(f"   (change it in Config page or set DASHBOARD_PASSWORD in .env)\n")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_dashboard()
