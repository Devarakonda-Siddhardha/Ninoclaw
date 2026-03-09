"""
General App Control skill — GPY (General Purpose) with Telugu natural language
Control apps using Android's accessibility service (GPY) for better app control
"""
import os
import json
from config import get_runtime_env

SKILL_INFO = {
    "name": "general_app_control",
    "description": "General app control using GPY with Telugu natural language",
    "version": "2.0",
    "icon": "📱",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "telugu_app_control",
            "description": "Control apps using Telugu natural language with GPY (General Purpose). Use when user says 'open YouTube', 'open Chrome', 'open app', 'బ్రువ్స' (browser), 'గూడ్లుస్తులు' (camera) in Telugu. Works for YouTube, Chrome, camera, WhatsApp, Instagram, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "App name to control, e.g., 'youtube', 'chrome', 'camera', 'whatsapp', 'instagram', 'spotify', 'netflix'"
                    },
                    "action": {
                        "type": "string",
                        "description": "What to do: 'open', 'close', 'start', 'stop', 'search', 'back', 'home', 'settings'"
                    }
                },
                "required": ["app_name"]
            }
        }
    }
]

# Telugu language responses
TELUGU_RESPONSES = {
    "greeting": "నమస్వు! నారి ఆపత్తులు!",
    "searching": "చూస్రువ్స వెతుస్తులు...",
    "found": "వెతులు కనుబడ!",
    "not_found": "క్షంగలేలు క్షంగలేలు!",
    "opening": "గూడ్లుస్తులు తెలుస్తులు!",
    "closing": "గూడ్లుస్తులు మూసితులు!",
    "success": "పూర్తులు ఆపత్తులు!",
    "sorry": "క్షంగలేలు క్షంగలేలు!",
    "help": "దయగోత్తులు తెలుందర్! ఏమ ఇష్ట్తులు అడుజడ?",
    "enjoy": "ఆనందర్! విండులుం!",
    "more_commands": "మరి పైండితులు నేత్తులు నుతుం!",
    "app_commands": {
        "open": "తెలుస్తులు",
        "close": "గూడ్లుస్తులు",
        "start": "ఆరంభ చేయు",
        "stop": "ఆరంభ ఆపందు",
        "search": "చూస్రువ్స",
        "back": "వెతులులు",
        "home": "హోము",
        "settings": "సెట్గలులు"
    }
}

# App control with GPY (General Purpose)
# GPY allows better accessibility control for Android apps
APP_CONTROL_GPY = {
    "youtube": {
        "telugu_name": "గూట్బ్",
        "package_name": "com.google.android.youtube",
        "gpy_action": "am start -n com.google.android.youtube"
    },
    "chrome": {
        "telugu_name": "గూట్బ్",
        "package_name": "com.android.chrome",
        "gpy_action": "am start -n com.android.chrome"
    },
    "camera": {
        "telugu_name": "గూడ్లుస్తులు",
        "package_name": "android.hardware.camera",
        "gpy_action": "am start -n android.hardware.camera"
    },
    "whatsapp": {
        "telugu_name": "వ్టాప్ట్స్",
        "package_name": "com.whatsapp",
        "gpy_action": "am start -n com.whatsapp"
    },
    "instagram": {
        "telugu_name": "ఇంస్టగ్రం",
        "package_name": "com.instagram.android",
        "gpy_action": "am start -n com.instagram.android"
    },
    "spotify": {
        "telugu_name": "స్టోటిల",
        "package_name": "com.spotify.music",
        "gpy_action": "am start -n com.spotify.music"
    },
    "netflix": {
        "telugu_name": "నేఫ్ల్క్స్",
        "package_name": "com.netflix.mediaclient",
        "gpy_action": "am start -n com.netflix.mediaclient"
    },
    "files": {
        "telugu_name": "దస్తులు",
        "package_name": "com.android.documentsui",
        "gpy_action": "am start -n com.android.documentsui"
    },
    "settings": {
        "telugu_name": "సెట్గలులు",
        "package_name": "com.android.settings",
        "gpy_action": "am start -n com.android.settings"
    }
}

def telugu_app_control(app_name, action, user_id=None):
    """Control an app using Telugu natural language and GPY (General Purpose)."""
    try:
        # Default user_id to config OWNER_ID if not provided
        if not user_id:
            from config import OWNER_ID
            user_id = str(OWNER_ID)

        # Get app info
        app_info = APP_CONTROL_GPY.get(app_name.lower())
        if not app_info:
            return f"{TELUGU_RESPONSES['not_found']}\n\n{TELUGU_RESPONSES['help']}\n\n{TELUGU_RESPONSES['app_commands']}\n" \
                       "గూట్బ్ (YouTube), గూడ్లుస్తులు (Chrome)\n" \
                       "గూడ్లుస్తులు (Camera), వ్టాప్ట్స్ (WhatsApp)\n" \
                       "ఇంస్టగ్రం (Instagram), స్టోటిల (Spotify)\n" \
                       "నేఫ్ల్క్స్ (Netflix), దస్తులు (Files), సెట్గలులు (Settings)\n\n" \
                       "చరోజ్: open, close, start, stop, search, back, home, settings"

            return telugu_app_control(app_name, action, user_id)

    except Exception as e:
        return f"❌ Telugu app control error: {str(e)}"

    return None
