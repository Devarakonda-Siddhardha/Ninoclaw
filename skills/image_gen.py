"""
Image generation skill.
Primary: fal.ai (FLUX.1 Schnell / FLUX.2) — fast, free tier, no rate limit issues
Fallback: Google Gemini Nano Banana (gemini-3.1-flash-image-preview)
"""
import os
import base64
import tempfile
import requests

SKILL_INFO = {
    "name": "image_gen",
    "description": "Generate images from text prompts using FLUX (fal.ai) or Gemini Nano Banana",
    "version": "2.0",
    "icon": "🎨",
    "author": "ninoclaw",
    "requires_key": True,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": "Generate an image from a text description/prompt. Use when user says 'generate an image', 'create a picture', 'draw', 'make an image of', 'show me a picture of', etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate"
                },
                "quality": {
                    "type": "string",
                    "description": "Quality: 'fast' (default, FLUX Schnell) or 'hd' (FLUX Dev, higher quality)",
                    "enum": ["fast", "hd"]
                }
            },
            "required": ["prompt"]
        }
    }
}]


def _generate_fal(prompt, quality, fal_key):
    """Generate image via fal.ai REST API (no SDK needed)."""
    model = "fal-ai/flux/schnell" if quality == "fast" else "fal-ai/flux/dev"
    url = f"https://fal.run/{model}"
    headers = {
        "Authorization": f"Key {fal_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "num_inference_steps": 4 if quality == "fast" else 28,
        "image_size": "landscape_4_3",
        "sync_mode": True,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    images = data.get("images", [])
    if not images:
        return None, "No image returned from fal.ai"
    img_url = images[0].get("url", "")
    if not img_url:
        return None, "No image URL in response"
    # Download the image
    img_resp = requests.get(img_url, timeout=60)
    img_resp.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir="/tmp")
    tmp.write(img_resp.content)
    tmp.close()
    return tmp.name, None


def _generate_gemini(prompt, gemini_key):
    """Generate image via Gemini Nano Banana API."""
    model = "gemini-3.1-flash-image-preview"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": gemini_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    image_b64 = None
    for part in parts:
        if "inlineData" in part:
            image_b64 = part["inlineData"].get("data", "")
    if not image_b64:
        return None, "No image returned from Gemini"
    img_bytes = base64.b64decode(image_b64)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir="/tmp")
    tmp.write(img_bytes)
    tmp.close()
    return tmp.name, None


def execute(tool_name, arguments):
    if tool_name != "generate_image":
        return None

    prompt = arguments.get("prompt", "").strip()
    quality = arguments.get("quality", "fast")

    if not prompt:
        return "❌ Please provide an image description."

    fal_key    = os.getenv("FAL_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    if not fal_key and not gemini_key:
        return "❌ No image generation API key found. Set FAL_KEY (fal.ai) or GEMINI_API_KEY in .env.\nGet a free fal.ai key at https://fal.ai"

    # Try fal.ai first (better free tier), fall back to Gemini
    errors = []
    if fal_key:
        try:
            path, err = _generate_fal(prompt, quality, fal_key)
            if path:
                return f"[IMAGE:{path}]\n🎨 {prompt}"
            errors.append(f"fal.ai: {err}")
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 401:
                errors.append("fal.ai: invalid API key")
            elif code == 429:
                errors.append("fal.ai: rate limited")
            else:
                errors.append(f"fal.ai: HTTP {code}")
        except Exception as e:
            errors.append(f"fal.ai: {e}")

    if gemini_key:
        try:
            path, err = _generate_gemini(prompt, gemini_key)
            if path:
                return f"[IMAGE:{path}]\n🎨 {prompt}"
            errors.append(f"Gemini: {err}")
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 429:
                errors.append("Gemini: rate limited (free tier exhausted)")
            else:
                errors.append(f"Gemini: HTTP {code}")
        except Exception as e:
            errors.append(f"Gemini: {e}")

    return f"❌ Image generation failed: {' | '.join(errors)}"


TOOLS = [{
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": "Generate an image from a text description/prompt. Use when user says 'generate an image', 'create a picture', 'draw', 'make an image of', 'show me', etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use: 'flash' (fast, default) or 'pro' (high quality)",
                    "enum": ["flash", "pro"]
                }
            },
            "required": ["prompt"]
        }
    }
}]

_MODELS = {
    "flash": "gemini-3.1-flash-image-preview",
    "pro":   "gemini-3-pro-image-preview",
}

def execute(tool_name, arguments):
    if tool_name != "generate_image":
        return None

    prompt = arguments.get("prompt", "").strip()
    model_key = arguments.get("model", "flash")
    model = _MODELS.get(model_key, _MODELS["flash"])

    if not prompt:
        return "❌ Please provide an image description."

    # Get API key — prefer GEMINI_API_KEY, fall back to OPENAI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        return "❌ No Gemini API key found. Set GEMINI_API_KEY in your .env file."

    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    # Try requested model, fall back to flash on rate limit
    models_to_try = [model] if model == _MODELS["flash"] else [model, _MODELS["flash"]]

    try:
        resp = None
        used_model = model
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code == 429 and m != models_to_try[-1]:
                continue  # try next model
            used_model = m
            resp.raise_for_status()
            break
        data = resp.json()

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        caption = ""
        image_b64 = None

        for part in parts:
            if "text" in part:
                caption = part["text"]
            elif "inlineData" in part:
                image_b64 = part["inlineData"].get("data", "")

        if not image_b64:
            return f"❌ No image returned. {caption or 'Try a different prompt.'}"

        # Save to temp file
        img_bytes = base64.b64decode(image_b64)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir="/tmp")
        tmp.write(img_bytes)
        tmp.close()

        caption_text = caption.strip() or f"🎨 {prompt}"
        # Return special marker so telegram_bot can send as photo
        return f"[IMAGE:{tmp.name}]\n{caption_text}"

    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code == 429:
            return "❌ Rate limit hit on all models. Wait a minute and try again (free tier limit)."
        if code == 400:
            return "❌ Image generation failed: prompt may violate content policy."
        return f"❌ API error: {e}"
    except Exception as e:
        return f"❌ Image generation failed: {e}"
