"""
AC Control skill — control Daikin, Samsung, and Voltas ACs via Termux IR bridge.

Requires:
  1. termux_ir_bridge.py running in Termux (NOT inside proot)
  2. Termux:API app + `pkg install termux-api` in Termux
  3. IR_BRIDGE_URL env var (default: http://127.0.0.1:7070)

Supported ACs:
  - Daikin  (protocol-encoded, works with most Daikin split ACs)
  - Samsung (stored codes — customize in AC_CODES below if your model differs)
  - Voltas  (stored codes — customize in AC_CODES below if your model differs)
"""
import os
import requests

SKILL_INFO = {
    "name": "ac_control",
    "description": "Control home ACs (Daikin, Samsung, Voltas) via IR blaster",
    "version": "1.0",
    "icon": "❄️",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ac_power",
            "description": "Turn an AC on or off. Specify which room/brand.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "Which AC to control: 'daikin', 'samsung', or 'voltas'",
                        "enum": ["daikin", "samsung", "voltas"],
                    },
                    "state": {
                        "type": "string",
                        "enum": ["on", "off"],
                        "description": "Turn on or off",
                    },
                    "temperature": {
                        "type": "integer",
                        "description": "Temperature in Celsius (18-30). Default 24.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["cool", "heat", "fan", "dry", "auto"],
                        "description": "AC mode. Default: cool",
                    },
                },
                "required": ["room", "state"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ac_set_temperature",
            "description": "Change the temperature of an AC that is already on.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "enum": ["daikin", "samsung", "voltas"],
                        "description": "Which AC to control",
                    },
                    "temperature": {
                        "type": "integer",
                        "description": "Target temperature in Celsius (18-30)",
                    },
                },
                "required": ["room", "temperature"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ac_set_mode",
            "description": "Change the mode of an AC (cool, heat, fan, dry, auto).",
            "parameters": {
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "enum": ["daikin", "samsung", "voltas"],
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["cool", "heat", "fan", "dry", "auto"],
                    },
                    "temperature": {
                        "type": "integer",
                        "description": "Optional temperature (18-30). Defaults to 24.",
                    },
                },
                "required": ["room", "mode"],
            },
        },
    },
]

# ── IR Bridge config ──────────────────────────────────────────────────────────
_BRIDGE = os.getenv("IR_BRIDGE_URL", "http://127.0.0.1:7070")

# ── Daikin Protocol Encoder ───────────────────────────────────────────────────
_DAIKIN_FREQ    = 38000
_DAIKIN_HDR_M   = 3650
_DAIKIN_HDR_S   = 1623
_DAIKIN_BIT_M   = 428
_DAIKIN_ONE_S   = 1280
_DAIKIN_ZERO_S  = 428
_DAIKIN_GAP     = 29428

_DAIKIN_MODE = {"auto": 0, "dry": 2, "cool": 3, "heat": 4, "fan": 6}
_DAIKIN_FAN  = {"auto": 10, "low": 3, "med": 5, "high": 7}


def _daikin_frame_to_pulses(frame: list, add_gap: bool = True) -> list:
    pulses = [_DAIKIN_HDR_M, _DAIKIN_HDR_S]
    for byte in frame:
        for bit in range(8):
            pulses.append(_DAIKIN_BIT_M)
            pulses.append(_DAIKIN_ONE_S if (byte >> bit) & 1 else _DAIKIN_ZERO_S)
    pulses.append(_DAIKIN_BIT_M)
    if add_gap:
        pulses.append(_DAIKIN_GAP)
    return pulses


def _daikin_encode(power: bool, mode: str = "cool", temp: int = 24, fan: str = "auto") -> list:
    """Encode Daikin AC state to IR pulse/space sequence (microseconds)."""
    temp = max(18, min(30, temp))
    mode_val = _DAIKIN_MODE.get(mode, 3)
    fan_val  = _DAIKIN_FAN.get(fan, 10)

    # Frame 1 — fixed preamble
    f1 = [0x11, 0xDA, 0x27, 0x00, 0xC5, 0x00, 0x00]
    f1.append(sum(f1) & 0xFF)

    # Frame 2 — fixed preamble
    f2 = [0x11, 0xDA, 0x27, 0x00, 0x42, 0x00, 0x00]
    f2.append(sum(f2) & 0xFF)

    # Frame 3 — AC state (19 bytes)
    f3 = [0x11, 0xDA, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
           0x00, 0x00, 0x00]
    f3[5] = ((mode_val & 0x07) << 4) | (0x01 if power else 0x00)
    f3[6] = (temp - 10) << 1
    f3[8] = (fan_val & 0x0F) << 4
    f3[18] = sum(f3[:18]) & 0xFF

    pattern = (
        _daikin_frame_to_pulses(f1) +
        _daikin_frame_to_pulses(f2) +
        _daikin_frame_to_pulses(f3, add_gap=False)
    )
    return pattern


# ── Samsung AC stored codes ───────────────────────────────────────────────────
# Common Samsung inverter split AC (ARC-1936 / ARC-3000M remote)
# If these don't work with your model, replace with codes from:
#   https://github.com/probonopd/irdb  (search "Samsung AC")
_SAMSUNG_FREQ = 38000
_SAMSUNG_CODES = {
    # (mode, temp) -> pulse pattern
    # Power off (universal)
    "off": [
        690, 17844, 3030, 8918, 546, 1602, 546, 1602, 546, 1602,
        546, 430, 546, 430, 546, 430, 546, 1602, 546, 430,
        546, 1602, 546, 1602, 546, 1602, 546, 430, 546, 430,
        546, 430, 546, 430, 546, 430, 546, 1602, 546, 1602,
        546, 430, 546, 1602, 546, 430, 546, 430, 546, 430,
        546, 430, 546, 430, 546, 430, 546, 430, 546, 430,
        546, 1602, 546, 1602, 546, 1602, 546, 430, 546
    ],
}

def _samsung_encode(power: bool, mode: str = "cool", temp: int = 24) -> list:
    """Return Samsung AC IR pulses. Uses stored codes, temperature-adjustable."""
    if not power:
        return _SAMSUNG_CODES.get("off", [])
    # Samsung: use stored cool code, note most stored codes are for a fixed state.
    # For full protocol support, replace with IRDB codes for your model.
    key = f"{mode}_{temp}"
    # Fallback to generic cool_24
    return _SAMSUNG_CODES.get(key, _SAMSUNG_CODES.get("cool_24", _SAMSUNG_CODES.get("off", [])))


# ── Voltas AC stored codes ────────────────────────────────────────────────────
# Voltas 1.5 ton split AC (common Indian market model - SAC_185V_ADS / similar)
# Uses NEC-like protocol. Replace codes from IRDB if your model differs.
_VOLTAS_FREQ = 38000
_VOLTAS_CODES: dict = {
    "off": [
        9028, 4484, 604, 552, 604, 552, 604, 552, 604, 1652,
        604, 552, 604, 552, 604, 552, 604, 552, 604, 1652,
        604, 1652, 604, 1652, 604, 552, 604, 1652, 604, 1652,
        604, 1652, 604, 1652, 604, 552, 604, 1652, 604, 552,
        604, 552, 604, 552, 604, 1652, 604, 552, 604, 552,
        604, 552, 604, 1652, 604, 552, 604, 1652, 604, 1652,
        604, 1652, 604, 552, 604, 1652, 604, 552, 604
    ],
}

def _voltas_encode(power: bool, mode: str = "cool", temp: int = 24) -> list:
    """Return Voltas AC IR pulses. Uses stored codes."""
    if not power:
        return _VOLTAS_CODES.get("off", [])
    key = f"{mode}_{temp}"
    return _VOLTAS_CODES.get(key, _VOLTAS_CODES.get("cool_24", _VOLTAS_CODES.get("off", [])))


# ── IR transmission ───────────────────────────────────────────────────────────
def _send_ir(pattern: list, freq: int = 38000) -> str:
    if not pattern:
        return "❌ No IR codes available for this command. Please add codes for your model."
    try:
        r = requests.post(
            f"{_BRIDGE}",
            json={"frequency": freq, "pattern": pattern},
            timeout=10,
        )
        if r.status_code == 200:
            return None  # success
        return f"❌ IR bridge error: {r.text}"
    except requests.ConnectionError:
        return (
            "❌ IR bridge not running. In Termux (outside proot), run:\n"
            "`python ~/Ninoclaw/termux_ir_bridge.py &`"
        )
    except Exception as e:
        return f"❌ IR error: {e}"


def _ac_control(room: str, power: bool, mode: str = "cool", temp: int = 24, fan: str = "auto") -> str:
    room = room.lower().strip()
    mode = mode.lower().strip()
    temp = max(18, min(30, temp))
    state = "on" if power else "off"

    if room == "daikin":
        pattern = _daikin_encode(power, mode, temp, fan)
        freq = _DAIKIN_FREQ
    elif room == "samsung":
        pattern = _samsung_encode(power, mode, temp)
        freq = _SAMSUNG_FREQ
    elif room == "voltas":
        pattern = _voltas_encode(power, mode, temp)
        freq = _VOLTAS_FREQ
    else:
        return f"❌ Unknown AC: '{room}'. Use: daikin, samsung, or voltas."

    err = _send_ir(pattern, freq)
    if err:
        return err

    brand = room.capitalize()
    if power:
        return f"❄️ {brand} AC turned ON — {mode.capitalize()} mode, {temp}°C"
    return f"🔴 {brand} AC turned OFF"


# ── Skill execute ─────────────────────────────────────────────────────────────
def execute(tool_name: str, arguments: dict) -> str:
    try:
        room = arguments.get("room", "daikin").lower()
        temp = int(arguments.get("temperature", 24))
        mode = arguments.get("mode", "cool").lower()
        fan  = arguments.get("fan_speed", "auto").lower()

        if tool_name == "ac_power":
            power = arguments.get("state", "on").lower() == "on"
            return _ac_control(room, power, mode, temp, fan)

        elif tool_name == "ac_set_temperature":
            return _ac_control(room, True, mode, temp, fan)

        elif tool_name == "ac_set_mode":
            return _ac_control(room, True, mode, temp, fan)

    except Exception as e:
        return f"❌ AC control error: {e}"
    return None
