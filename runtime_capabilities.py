"""
Local runtime capability detection for Ninoclaw.

This module is intentionally conservative:
- detect only local OS/hardware/runtime capabilities
- do not collect unique device identifiers
- do not send any telemetry anywhere
"""
import ctypes
import importlib.util
import os
import platform
import shutil
from functools import lru_cache
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def _detect_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return (
        bool(os.environ.get("TERMUX_VERSION"))
        or "com.termux" in prefix
        or "termux" in prefix.lower()
    )


def _detect_device_model() -> str:
    candidates = [
        Path("/sys/firmware/devicetree/base/model"),
        Path("/proc/device-tree/model"),
    ]
    for path in candidates:
        text = _read_text(path).replace("\x00", "").strip()
        if text:
            return text

    cpuinfo = _read_text(Path("/proc/cpuinfo"))
    for line in cpuinfo.splitlines():
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        if key.lower() in {"model", "hardware"} and value:
            return value

    return platform.platform()


def _memory_bytes() -> int:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return int(stat.ullTotalPhys)

    meminfo = _read_text(Path("/proc/meminfo"))
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        return int(page_size) * int(pages)
    except Exception:
        return 0


def _has_display(is_termux: bool) -> bool:
    if os.name == "nt":
        return True
    if is_termux:
        return False
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _which_any(*names: str) -> bool:
    return any(shutil.which(name) for name in names)


def _has_python_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _bool_env(name: str) -> bool:
    return bool((os.environ.get(name) or "").strip())


def _profile_name(low_resource: bool, ram_gb: float) -> str:
    if low_resource:
        return "low-resource"
    if ram_gb and ram_gb < 4:
        return "standard"
    return "full"


@lru_cache(maxsize=1)
def _detect_capabilities_cached():
    system = platform.system().lower()
    machine = platform.machine().lower()
    is_termux = _detect_termux()
    device_model = _detect_device_model()
    model_lower = device_model.lower()
    ram_bytes = _memory_bytes()
    ram_gb = round(ram_bytes / (1024 ** 3), 1) if ram_bytes else 0.0

    is_windows = system == "windows"
    is_linux = system == "linux"
    is_macos = system == "darwin"
    is_raspberry_pi = "raspberry pi" in model_lower
    is_pi_zero_class = is_raspberry_pi and ("zero" in model_lower or ram_gb and ram_gb <= 1.2)
    low_resource = bool((ram_bytes and ram_bytes < 2 * 1024 ** 3) or is_pi_zero_class)

    has_display = _has_display(is_termux)
    has_node = _which_any("node", "node.exe")
    has_npx = _which_any("npx", "npx.cmd")
    has_ollama = _which_any("ollama", "ollama.exe")
    has_mss = _has_python_module("mss")
    has_pillow = _has_python_module("PIL")
    has_music_bridge = _bool_env("MUSIC_BRIDGE_URL")
    has_ir_bridge = _bool_env("IR_BRIDGE_URL")

    supports = {
        "expo": has_node and has_npx and not is_termux and not low_resource,
        "app_launcher": is_windows,
        "screenshot": has_display and (is_windows or has_mss or has_pillow),
        "music_control": is_windows or has_music_bridge,
        "music_play": has_music_bridge or has_display,
        "local_ollama": has_ollama and not low_resource,
        "ir_bridge": has_ir_bridge,
    }

    return {
        "platform": platform.system(),
        "release": platform.release(),
        "machine": machine,
        "device_model": device_model,
        "is_windows": is_windows,
        "is_linux": is_linux,
        "is_macos": is_macos,
        "is_termux": is_termux,
        "is_raspberry_pi": is_raspberry_pi,
        "is_pi_zero_class": is_pi_zero_class,
        "ram_bytes": ram_bytes,
        "ram_gb": ram_gb,
        "low_resource": low_resource,
        "profile": _profile_name(low_resource, ram_gb),
        "has_display": has_display,
        "has_node": has_node,
        "has_npx": has_npx,
        "has_ollama": has_ollama,
        "has_mss": has_mss,
        "has_pillow": has_pillow,
        "has_music_bridge": has_music_bridge,
        "has_ir_bridge": has_ir_bridge,
        "supports": supports,
    }


def detect_capabilities(force_refresh: bool = False) -> dict:
    if force_refresh:
        _detect_capabilities_cached.cache_clear()
    return dict(_detect_capabilities_cached())


_TOOL_SUPPORT_RULES = {
    "open_app": ("app_launcher", "App launcher is only available on Windows."),
    "close_app": ("app_launcher", "App launcher is only available on Windows."),
    "list_running_apps": ("app_launcher", "App launcher is only available on Windows."),
    "take_screenshot": ("screenshot", "Screenshot capture needs a supported desktop/display environment."),
    "music_play": ("music_play", "Music playback needs a desktop browser session or MUSIC_BRIDGE_URL."),
    "music_pause": ("music_control", "Music control needs Windows media keys or MUSIC_BRIDGE_URL."),
    "music_next": ("music_control", "Music control needs Windows media keys or MUSIC_BRIDGE_URL."),
    "music_previous": ("music_control", "Music control needs Windows media keys or MUSIC_BRIDGE_URL."),
    "music_volume": ("music_control", "Music control needs Windows media keys or MUSIC_BRIDGE_URL."),
    "expo_create_app": ("expo", "Expo tools require Node/npx and at least about 2 GB RAM. They are disabled on low-resource or Termux devices."),
    "expo_edit_app": ("expo", "Expo tools require Node/npx and at least about 2 GB RAM. They are disabled on low-resource or Termux devices."),
    "expo_start_app": ("expo", "Expo tools require Node/npx and at least about 2 GB RAM. They are disabled on low-resource or Termux devices."),
    "expo_stop_app": ("expo", "Expo tools require Node/npx and at least about 2 GB RAM. They are disabled on low-resource or Termux devices."),
    "expo_list_apps": ("expo", "Expo tools require Node/npx and at least about 2 GB RAM. They are disabled on low-resource or Termux devices."),
    "expo_delete_app": ("expo", "Expo tools require Node/npx and at least about 2 GB RAM. They are disabled on low-resource or Termux devices."),
}


def tool_unavailable_reason(tool_name: str, capabilities: dict | None = None) -> str | None:
    capabilities = capabilities or detect_capabilities()
    rule = _TOOL_SUPPORT_RULES.get(tool_name)
    if not rule:
        return None
    capability_key, reason = rule
    if capabilities.get("supports", {}).get(capability_key, False):
        return None
    return reason


def summarized_capability_report(capabilities: dict | None = None) -> dict:
    capabilities = capabilities or detect_capabilities()
    supports = capabilities.get("supports", {})
    disabled = []
    for tool_name in sorted(_TOOL_SUPPORT_RULES):
        reason = tool_unavailable_reason(tool_name, capabilities)
        if reason:
            disabled.append({"tool": tool_name, "reason": reason})
    return {
        "profile": capabilities.get("profile", "standard"),
        "device": capabilities.get("device_model") or f"{capabilities.get('platform')} {capabilities.get('machine')}",
        "ram_gb": capabilities.get("ram_gb", 0.0),
        "supports": supports,
        "disabled_tools": disabled,
    }


def recommended_env_overrides(existing_env: dict | None = None, capabilities: dict | None = None) -> dict:
    """
    Return conservative environment overrides for the current device profile.

    This is intentionally narrow:
    - disable incompatible heavy/platform-specific skills
    - do not rewrite model provider settings automatically
    """
    existing_env = existing_env or {}
    capabilities = capabilities or detect_capabilities()

    disabled_skills = {
        item.strip()
        for item in str(existing_env.get("DISABLED_SKILLS", "")).split(",")
        if item.strip()
    }

    if not capabilities.get("supports", {}).get("app_launcher", False):
        disabled_skills.add("app_launcher")

    if not capabilities.get("supports", {}).get("expo", False):
        disabled_skills.add("expo_builder")

    if not capabilities.get("supports", {}).get("screenshot", False):
        disabled_skills.add("screenshot")

    music_supported = (
        capabilities.get("supports", {}).get("music_control", False)
        or capabilities.get("supports", {}).get("music_play", False)
    )
    if not music_supported:
        disabled_skills.add("youtube_music")

    return {
        "DISABLED_SKILLS": ",".join(sorted(disabled_skills))
    }
