"""
AI integration with OpenAI API and Ollama
"""
import requests
import json
from typing import Dict, Any, Optional, Tuple
from config import (
    AI_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_API_URL, OPENAI_MODEL
)


def chat(message, system_prompt=None, history=None, tools=None, image_b64=None):
    """
    Send a message to AI and get a response

    Args:
        message: User's message
        system_prompt: Optional system prompt
        history: Optional conversation history as list of messages
        tools: Optional list of tools/functions the AI can call
        image_b64: Optional base64-encoded image (JPEG) for vision

    Returns:
        AI response text
    """
    if AI_PROVIDER == "openai":
        return _chat_openai(message, system_prompt, history, tools, image_b64)
    else:
        return _chat_ollama(message, system_prompt, history, tools)

def _chat_openai(message, system_prompt=None, history=None, tools=None, image_b64=None):
    """Chat using OpenAI-compatible API (supports GPT-4, Claude, Gemini, etc.)"""
    url = f"{OPENAI_API_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = []

    # Add system prompt
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    # Add history
    if history:
        messages.extend(history)

    # Add current message (with optional image)
    if image_b64:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message or "What's in this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": message
        })

    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7
    }

    # Add tools if provided
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        assistant_message = data["choices"][0]["message"]

        # Check if AI wants to call a tool
        if "tool_calls" in assistant_message:
            tool_calls = assistant_message["tool_calls"]
            return {
                "content": assistant_message.get("content", ""),
                "tool_calls": tool_calls
            }

        return assistant_message.get("content", "").strip()

    except requests.RequestException as e:
        return {"content": f"Error connecting to API: {e}", "tool_calls": None}
    except (KeyError, IndexError) as e:
        return {"content": f"Error parsing API response: {e}", "tool_calls": None}

    except requests.RequestException as e:
        return {"content": f"Error connecting to API: {e}", "tool_calls": None}
    except (KeyError, IndexError) as e:
        return {"content": f"Error parsing API response: {e}", "tool_calls": None}

def _chat_ollama(message, system_prompt=None, history=None, tools=None):
    """Chat using local Ollama"""
    url = f"{OLLAMA_HOST}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": []
    }

    # Add system prompt
    if system_prompt:
        payload["messages"].append({
            "role": "system",
            "content": system_prompt
        })

    # Add history
    if history:
        payload["messages"].extend(history)

    # Add current message
    payload["messages"].append({
        "role": "user",
        "content": message
    })

    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        # Read streaming response
        full_response = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "message" in data and "content" in data["message"]:
                    full_response += data["message"]["content"]

        return full_response.strip()

    except requests.RequestException as e:
        return f"Error connecting to Ollama: {e}"

def list_models():
    """List available models"""
    if AI_PROVIDER == "openai":
        return [OPENAI_MODEL]  # Simplified for API
    else:
        return _list_ollama_models()

def _list_ollama_models():
    """List available Ollama models"""
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except requests.RequestException:
        return []

def test_connection():
    """Test if AI service is accessible"""
    if AI_PROVIDER == "openai":
        return _test_openai_connection()
    else:
        return _test_ollama_connection()

def _test_openai_connection():
    """Test OpenAI API connection"""
    try:
        url = f"{OPENAI_API_URL}/models"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False

def _test_ollama_connection():
    """Test Ollama connection"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False
