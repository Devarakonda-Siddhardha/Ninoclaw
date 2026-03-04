"""
AI integration — supports a chain of models with automatic fallback
"""
import requests
import json
import time
from config import MODELS, OLLAMA_HOST, OLLAMA_MODEL


def chat(message, system_prompt=None, history=None, tools=None, image_b64=None):
    """
    Try each model in MODELS chain in order.
    Falls back to the next model on 429, 5xx, or connection errors.
    """
    last_error = "No models configured."

    for model_cfg in MODELS:
        result, error = _try_openai(model_cfg, message, system_prompt, history, tools, image_b64)
        if result is not None:
            return result
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

    for model_cfg in MODELS:
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

        try:
            async with httpx.AsyncClient(timeout=60) as client:
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


def _try_openai(model_cfg, message, system_prompt, history, tools, image_b64):
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
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        for attempt in range(3):
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
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
            return {"content": msg.get("content", ""), "tool_calls": msg["tool_calls"]}, None

        return msg.get("content", "").strip(), None

    except requests.RequestException as e:
        return None, str(e)
    except (KeyError, IndexError) as e:
        return None, f"Parse error: {e}"


# ── Ollama (kept for legacy / local use) ──────────────────────────────────

def _chat_ollama(message, system_prompt=None, history=None):
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {"model": OLLAMA_MODEL, "messages": []}
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
    return [m["model"] for m in MODELS]


def test_connection():
    if not MODELS:
        return False
    cfg = MODELS[0]
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


