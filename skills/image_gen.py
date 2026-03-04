"""
Image generation skill using Google Gemini native image generation API.
Requires GEMINI_API_KEY (or OPENAI_API_KEY when using Gemini provider).
Model: gemini-3.1-flash-image-preview
"""
import os
import base64
import tempfile
import requests

SKILL_INFO = {
    "name": "image_gen",
    "description": "Generate images from text prompts using Gemini image generation",
    "version": "1.0",
    "icon": "🎨",
    "author": "ninoclaw",
    "requires_key": True,
}

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
