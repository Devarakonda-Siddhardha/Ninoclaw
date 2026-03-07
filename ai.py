"""
AI integration — supports a chain of models with automatic fallback
"""
import requests
import json
import time
from config import get_runtime_ai_config


# Keywords that signal a complex/expensive request
_COMPLEX_KEYWORDS = {
    "code", "write", "debug", "fix", "build", "create", "implement", "program",
    "analyze", "analyse", "research", "compare", "explain in detail", "essay",
    "summarize", "summarise", "plan", "design", "architecture", "optimize",
    "translate", "refactor", "review", "generate", "draft", "report",
}

# These keywords indicate tool use is needed — always route to smart model
_TOOL_KEYWORDS = {
    "play", "pause", "skip", "spotify", "song", "music", "volume", "track",
    "slack", "github", "issue", "pull request", "calendar", "schedule", "event",
    "weather", "news", "calculate", "convert", "currency", "search", "image",
    "remind", "reminder", "cron", "what's playing", "next song",
}

def _pick_model_cfg(message: str, runtime_cfg: dict, force_smart: bool = False, force_fast: bool = False):
    """
    Route to fast or smart model based on request complexity.
    Returns a model config dict, or None to use the normal MODELS chain.
    Only activates when FAST_MODEL is configured.
    """
    if not runtime_cfg.get("fast_model"):
        return None  # routing disabled, use normal chain
    if force_fast:
        return runtime_cfg.get("fast_cfg")
    if force_smart:
        return runtime_cfg.get("smart_cfg")
    msg_lower = message.lower()
    is_complex = (
        len(message) > 300
        or any(kw in msg_lower for kw in _COMPLEX_KEYWORDS)
        or any(kw in msg_lower for kw in _TOOL_KEYWORDS)
    )
    return runtime_cfg.get("smart_cfg") if is_complex else runtime_cfg.get("fast_cfg")

def _try_gemini_tools(message, system_prompt, history, tools):
    """
    Use Gemini Flash via Google API for tool/function calling.
    More reliable than OpenRouter free models for tool use.
    """
    import os
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        return None, "No GEMINI_API_KEY"

    model = "gemini-3-flash-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers_g = {"x-goog-api-key": gemini_key, "Content-Type": "application/json"}

    # Build contents
    contents = []
    if history:
        for h in history[-10:]:
            role = "user" if h.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    # Convert OpenAI tool format to Gemini format
    gemini_tools = []
    if tools:
        fn_decls = []
        for t in tools:
            fn = t.get("function", {})
            fn_decls.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            })
        gemini_tools = [{"function_declarations": fn_decls}]

    payload = {
        "contents": contents,
    }
    if gemini_tools:
        payload["tools"] = gemini_tools
        payload["tool_config"] = {"function_calling_config": {"mode": "AUTO"}}
    if system_prompt:
        payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

    try:
        resp = requests.post(url, json=payload, headers=headers_g, timeout=60)
        if resp.status_code == 429:
            return None, "Gemini rate limited"
        resp.raise_for_status()
        data = resp.json()
        candidate = data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])

        # Check for function call
        for part in parts:
            if "functionCall" in part:
                fc = part["functionCall"]
                return {
                    "content": "",
                    "tool_calls": [{"function": {"name": fc["name"], "arguments": fc.get("args", {})}}]
                }, None

        # Text response
        text = "".join(p.get("text", "") for p in parts)
        return {"content": text, "tool_calls": None}, None
    except Exception as e:
        return None, str(e)


def chat(message, system_prompt=None, history=None, tools=None, image_b64=None, force_smart=False, force_fast=False):
    """
    Try each model in MODELS chain in order.
    Falls back to the next model on 429, 5xx, or connection errors.
    If FAST_MODEL is configured, routes simple vs complex requests automatically.
    """
    last_error = "No models configured."
    runtime_cfg = get_runtime_ai_config()

    routed = _pick_model_cfg(message, runtime_cfg, force_smart=force_smart, force_fast=force_fast)
    model_list = [routed] if routed else runtime_cfg["models"]
    for model_cfg in model_list:
        result, error = _try_openai(
            model_cfg, message, system_prompt, history, tools, image_b64, runtime_cfg["ollama_think"]
        )
        if result is not None:
            return result
        # If failed with image, retry without it (non-multimodal model).
        # The image URL is already embedded in the text message by the caller.
        if image_b64 and ("400" in str(error) or "Bad Request" in str(error)):
            print(f"[AI] Model {model_cfg['model']} rejected image payload, retrying text-only...")
            result, error2 = _try_openai(
                model_cfg, message, system_prompt, history, tools, None, runtime_cfg["ollama_think"]
            )
            if result is not None:
                return result
            error = error2
        last_error = error
        print(f"[AI] Model {model_cfg['model']} failed ({error}), trying next...")

    return f"⚠️ All models failed. Last error: {last_error}"


async def chat_stream(message, system_prompt=None, history=None):
    """
    Async generator that yields text chunks as they stream in.
    Falls back to non-streaming chat() if streaming fails.
    Only used when no tool calls needed (plain conversation).
    """
    import asyncio, httpx
    last_error = "No models configured."
    runtime_cfg = get_runtime_ai_config()

    routed = _pick_model_cfg(message, runtime_cfg)
    model_list = [routed] if routed else runtime_cfg["models"]

    for model_cfg in model_list:
        url = f"{model_cfg['api_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {model_cfg['api_key']}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model_cfg["model"],
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        if model_cfg.get("api_key") == "ollama" or "localhost:11434" in url:
            payload["think"] = runtime_cfg["ollama_think"]

        try:
            _timeout = 180 if (model_cfg.get("api_key") == "ollama" or "localhost:11434" in url) else 60
            async with httpx.AsyncClient(timeout=_timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code >= 400:
                        last_error = f"HTTP {resp.status_code}"
                        continue
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content") or ""
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
            return  # success
        except Exception as e:
            last_error = str(e)
            print(f"[AI] Stream failed for {model_cfg['model']} ({e}), trying next...")
            continue

    # All models failed — yield error as plain text
    yield f"⚠️ All models failed. Last error: {last_error}"


def _try_openai(model_cfg, message, system_prompt, history, tools, image_b64, ollama_think=False):
    """
    Single attempt against one model config.
    Returns (result, None) on success, (None, error_str) on failure.
    """
    url = f"{model_cfg['api_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['api_key']}",
        "Content-Type": "application/json"
    }

    messages = []
    _is_ollama = model_cfg.get("api_key") == "ollama" or "localhost:11434" in url
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)

    if image_b64:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message or "What's in this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        })
    else:
        messages.append({"role": "user", "content": message})

    payload = {"model": model_cfg["model"], "messages": messages, "temperature": 0.7}
    if _is_ollama:
        payload["think"] = ollama_think  # Qwen3 thinking mode (toggle via: ninoclaw think on/off)
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        for attempt in range(3):
            _timeout = 180 if (headers.get("Authorization", "") == "Bearer ollama" or "localhost:11434" in url) else 60
            resp = requests.post(url, json=payload, headers=headers, timeout=_timeout)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 500:
                return None, f"HTTP {resp.status_code}"
            resp.raise_for_status()
            break
        else:
            return None, "Rate limited after 3 retries"

        data = resp.json()
        msg = data["choices"][0]["message"]

        if "tool_calls" in msg:
            return {"content": msg.get("content") or "", "tool_calls": msg["tool_calls"]}, None

        return (msg.get("content") or "").strip(), None

    except requests.RequestException as e:
        return None, str(e)
    except (KeyError, IndexError) as e:
        return None, f"Parse error: {e}"


# ── Ollama (kept for legacy / local use) ──────────────────────────────────

def _chat_ollama(message, system_prompt=None, history=None):
    runtime_cfg = get_runtime_ai_config()
    url = f"{runtime_cfg['ollama_host']}/api/chat"
    payload = {"model": runtime_cfg["ollama_model"], "messages": []}
    if system_prompt:
        payload["messages"].append({"role": "system", "content": system_prompt})
    if history:
        payload["messages"].extend(history)
    payload["messages"].append({"role": "user", "content": message})

    try:
        resp = requests.post(url, json=payload, stream=True)
        resp.raise_for_status()
        full = ""
        for line in resp.iter_lines():
            if line:
                d = json.loads(line)
                if "message" in d and "content" in d["message"]:
                    full += d["message"]["content"]
        return full.strip()
    except requests.RequestException as e:
        return f"Error connecting to Ollama: {e}"


def list_models():
    return [m["model"] for m in get_runtime_ai_config()["models"]]


def test_connection():
    runtime_cfg = get_runtime_ai_config()
    if not runtime_cfg["models"]:
        return False
    cfg = runtime_cfg["models"][0]
    try:
        url = f"{cfg['api_url']}/models"
        headers = {"Authorization": f"Bearer {cfg['api_key']}"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return True
        # Ollama fallback: try native /api/tags endpoint
        if cfg.get("api_key") == "ollama" or "localhost:11434" in cfg["api_url"]:
            base = cfg["api_url"].rstrip("/").removesuffix("/v1")
            r2 = requests.get(f"{base}/api/tags", timeout=10)
            return r2.status_code == 200
        return False
    except requests.RequestException:
        # Ollama fallback on connection error too
        try:
            if cfg.get("api_key") == "ollama" or "localhost:11434" in cfg["api_url"]:
                base = cfg["api_url"].rstrip("/").removesuffix("/v1")
                r2 = requests.get(f"{base}/api/tags", timeout=10)
                return r2.status_code == 200
        except Exception:
            pass
        return False


