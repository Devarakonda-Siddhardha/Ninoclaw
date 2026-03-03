"""
System info skill — CPU, RAM, storage, uptime (no dependencies)
"""
import os, platform

SKILL_INFO = {
    "name": "system_info",
    "description": "Get device system info: RAM, storage, uptime, OS",
    "version": "1.0",
    "icon": "📊",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_system_info",
        "description": "Get current device stats: memory usage, disk space, uptime, OS info",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}]

def execute(tool_name, arguments):
    if tool_name != "get_system_info":
        return None
    lines = []
    try:
        lines.append(f"🖥️ OS: {platform.system()} {platform.release()}")
        lines.append(f"🏗️ Arch: {platform.machine()}")
        lines.append(f"🐍 Python: {platform.python_version()}")

        # RAM from /proc/meminfo
        if os.path.exists("/proc/meminfo"):
            mem = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    mem[parts[0].rstrip(":")] = int(parts[1])
            total_mb = mem.get("MemTotal", 0) // 1024
            avail_mb = mem.get("MemAvailable", 0) // 1024
            used_mb  = total_mb - avail_mb
            pct = round(used_mb / total_mb * 100) if total_mb else 0
            lines.append(f"💾 RAM: {used_mb}MB / {total_mb}MB used ({pct}%)")

        # Uptime from /proc/uptime
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            lines.append(f"⏱️ Uptime: {h}h {m}m")

        # Disk
        st = os.statvfs("/")
        total_gb = st.f_blocks * st.f_frsize / 1024**3
        free_gb  = st.f_bavail * st.f_frsize / 1024**3
        used_gb  = total_gb - free_gb
        lines.append(f"💿 Disk: {used_gb:.1f}GB / {total_gb:.1f}GB ({round(used_gb/total_gb*100)}%)")

    except Exception as e:
        lines.append(f"Error: {e}")
    return "\n".join(lines)
