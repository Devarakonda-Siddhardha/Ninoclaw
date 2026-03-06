"""
Image generation skill.
Primary: fal.ai (FLUX.1 Schnell / FLUX.2) — fast, free tier, no rate limit issues
Fallback: Google Gemini Nano Banana (gemini-3.1-flash-image-preview)
"""
import os
import base64
import tempfile
import uuid
from pathlib import Path
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


def _tmp_png_file():
    return tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=tempfile.gettempdir())


def _persist_for_web(temp_path):
    """Copy generated image into websites/assets and return public URL."""
    try:
        project_root = Path(__file__).resolve().parents[1]
        assets_dir = project_root / "websites" / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        filename = f"gen_{uuid.uuid4().hex[:12]}.png"
        dest = assets_dir / filename
        dest.write_bytes(Path(temp_path).read_bytes())
        port = os.getenv("DASHBOARD_PORT", "8080")
        return f"http://localhost:{port}/builds-assets/{filename}"
    except Exception:
        return ""


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
    tmp = _tmp_png_file()
    tmp.write(img_resp.content)
    tmp.close()
    return tmp.name, None


def _generate_hf(prompt, hf_token):
    """Generate image via HuggingFace Inference API (FLUX.1-schnell, free)."""
    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": prompt}
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    tmp = _tmp_png_file()
    tmp.write(resp.content)
    tmp.close()
    return tmp.name, None


def _generate_gemini(prompt, gemini_key):
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
    tmp = _tmp_png_file()
    tmp.write(img_bytes)
    tmp.close()
    return tmp.name, None


def execute(tool_name, arguments):
    if tool_name != "generate_image":
        return None

    prompt = arguments.get("prompt", "").strip()
    # Accept both 'quality' and 'model' arg names (some models hallucinate 'model')
    quality = arguments.get("quality") or arguments.get("model", "fast")
    if quality in ("pro", "hd", "high", "best"):
        quality = "hd"
    else:
        quality = "fast"

    if not prompt:
        return "❌ Please provide an image description."

    fal_key    = os.getenv("FAL_KEY", "")
    hf_token   = os.getenv("HF_TOKEN", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    if not fal_key and not hf_token and not gemini_key:
        return "❌ No image generation key found. Set HF_TOKEN (free at huggingface.co), FAL_KEY, or GEMINI_API_KEY in .env."

    # Try fal.ai → HuggingFace → Gemini
    errors = []
    if fal_key:
        try:
            path, err = _generate_fal(prompt, quality, fal_key)
            if path:
                image_url = _persist_for_web(path)
                if image_url:
                    return f"[IMAGE:{path}]\n[IMAGE_URL:{image_url}]\n🎨 {prompt}"
                return f"[IMAGE:{path}]\n🎨 {prompt}"
            errors.append(f"fal.ai: {err}")
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            errors.append(f"fal.ai: HTTP {code}")
        except Exception as e:
            errors.append(f"fal.ai: {e}")

    if hf_token:
        try:
            path, err = _generate_hf(prompt, hf_token)
            if path:
                image_url = _persist_for_web(path)
                if image_url:
                    return f"[IMAGE:{path}]\n[IMAGE_URL:{image_url}]\n🎨 {prompt}"
                return f"[IMAGE:{path}]\n🎨 {prompt}"
            errors.append(f"HuggingFace: {err}")
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 503:
                errors.append("HuggingFace: model loading, try again in 20s")
            else:
                errors.append(f"HuggingFace: HTTP {code}")
        except Exception as e:
            errors.append(f"HuggingFace: {e}")

    if gemini_key:
        try:
            path, err = _generate_gemini(prompt, gemini_key)
            if path:
                image_url = _persist_for_web(path)
                if image_url:
                    return f"[IMAGE:{path}]\n[IMAGE_URL:{image_url}]\n🎨 {prompt}"
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

