"""
SSH Control Skill — run commands on remote servers via Telegram
Uses paramiko. Install: pip install paramiko
Hosts stored in .env as SSH_HOSTS (JSON) or managed via add/remove tools.
"""
import json
import os
import re

SKILL_INFO = {
    "name": "ssh_control",
    "description": "SSH into remote servers and run commands. Manage saved hosts.",
    "version": "1.0",
    "icon": "🖥️",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ssh_run",
            "description": (
                "Run a shell command on a saved SSH server. "
                "Use when user says 'ssh into X and run Y', 'run Y on my Pi', "
                "'execute Y on server X', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "host_alias": {
                        "type": "string",
                        "description": "Alias of the saved host (e.g. 'pi', 'vps'). Use ssh_list_hosts to see saved hosts."
                    },
                    "command": {
                        "type": "string",
                        "description": "Shell command to run on the remote server"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds (default 30)"
                    }
                },
                "required": ["host_alias", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_list_hosts",
            "description": "List all saved SSH hosts/servers",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_add_host",
            "description": (
                "Save a new SSH host so the bot can connect to it. "
                "Use when user says 'add SSH host', 'save server', 'connect to X via SSH'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "alias":    {"type": "string", "description": "Short name for this host, e.g. 'pi' or 'vps'"},
                    "hostname": {"type": "string", "description": "IP address or hostname"},
                    "port":     {"type": "integer", "description": "SSH port (default 22)"},
                    "username": {"type": "string", "description": "SSH username"},
                    "password": {"type": "string", "description": "SSH password (leave empty if using key)"},
                    "key_path": {"type": "string", "description": "Path to private key file, e.g. ~/.ssh/id_rsa (optional)"}
                },
                "required": ["alias", "hostname", "username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_remove_host",
            "description": "Remove a saved SSH host by alias",
            "parameters": {
                "type": "object",
                "properties": {
                    "alias": {"type": "string", "description": "Alias of the host to remove"}
                },
                "required": ["alias"]
            }
        }
    },
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _hosts_file():
    return os.path.join(os.path.dirname(__file__), "..", "ssh_hosts.json")

def _load_hosts() -> dict:
    path = _hosts_file()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_hosts(hosts: dict):
    with open(_hosts_file(), "w") as f:
        json.dump(hosts, f, indent=2)

# ── Tool execution ────────────────────────────────────────────────────────────

def execute(tool_name: str, arguments: dict) -> str:
    if tool_name == "ssh_list_hosts":
        hosts = _load_hosts()
        if not hosts:
            return "No SSH hosts saved yet.\nUse: \"add SSH host alias=pi host=192.168.x.x user=pi\""
        lines = ["🖥️ **Saved SSH Hosts:**\n"]
        for alias, h in hosts.items():
            auth = "🔑 key" if h.get("key_path") else "🔒 password"
            lines.append(f"• **{alias}** → {h['username']}@{h['hostname']}:{h.get('port',22)} ({auth})")
        return "\n".join(lines)

    if tool_name == "ssh_add_host":
        alias = re.sub(r'[^a-z0-9_\-]', '', arguments.get("alias", "").lower())
        if not alias:
            return "❌ Invalid alias."
        hosts = _load_hosts()
        hosts[alias] = {
            "hostname": arguments["hostname"],
            "port":     int(arguments.get("port", 22)),
            "username": arguments["username"],
            "password": arguments.get("password", ""),
            "key_path": arguments.get("key_path", ""),
        }
        _save_hosts(hosts)
        return f"✅ Host **{alias}** saved ({arguments['username']}@{arguments['hostname']})"

    if tool_name == "ssh_remove_host":
        alias = arguments.get("alias", "").lower()
        hosts = _load_hosts()
        if alias not in hosts:
            return f"❌ Host '{alias}' not found."
        del hosts[alias]
        _save_hosts(hosts)
        return f"🗑️ Host '{alias}' removed."

    if tool_name == "ssh_run":
        host_alias = arguments.get("host_alias", "").lower()
        command = arguments.get("command", "").strip()
        timeout = int(arguments.get("timeout", 30))

        if not command:
            return "❌ No command specified."

        # Block dangerous commands
        _BLOCKED = ["rm -rf /", "mkfs", ":(){:|:&};:", "dd if=/dev/zero of=/dev/"]
        for blocked in _BLOCKED:
            if blocked in command:
                return f"❌ Blocked dangerous command: `{blocked}`"

        hosts = _load_hosts()
        if host_alias not in hosts:
            available = ", ".join(hosts.keys()) or "none"
            return f"❌ Host '{host_alias}' not found.\nSaved hosts: {available}"

        h = hosts[host_alias]
        try:
            import paramiko
        except ImportError:
            return "❌ paramiko not installed.\nRun: `pip install paramiko`"

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            connect_kwargs = dict(
                hostname=h["hostname"],
                port=h.get("port", 22),
                username=h["username"],
                timeout=10,
            )
            key_path = h.get("key_path", "")
            if key_path:
                connect_kwargs["key_filename"] = os.path.expanduser(key_path)
            elif h.get("password"):
                connect_kwargs["password"] = h["password"]

            client.connect(**connect_kwargs)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            exit_code = stdout.channel.recv_exit_status()
            client.close()

            result = f"🖥️ `{host_alias}` → `{command}`\n\n"
            if out:
                result += f"```\n{out[:3000]}\n```"
            if err:
                result += f"\n⚠️ stderr:\n```\n{err[:500]}\n```"
            if not out and not err:
                result += "_(no output)_"
            if exit_code != 0:
                result += f"\n\n↩️ Exit code: {exit_code}"
            return result

        except Exception as e:
            client.close()
            return f"❌ SSH failed: {e}"

    return None
