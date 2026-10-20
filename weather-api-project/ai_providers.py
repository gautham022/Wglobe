"""
ai_providers.py

Multi-provider LLM client for the Wglobe chatbot.

Tries providers in order and uses the first one that works:
  1. Groq          (GROQ_API_KEY)      - Llama 3.3 70B, generous free tier
  2. Google Gemini (GEMINI_API_KEY)    - gemini-2.0-flash free tier
  3. HuggingFace   (HUGGINGFACE_API_KEY) - Inference API (OpenAI-compatible router)

Groq gives ~6k tokens/min on the free tier which is far more headroom than a
single Gemini key, so the chatbot keeps working even when one provider is
rate-limited. Any provider that errors or is throttled is skipped automatically.

Env vars (all optional - whatever exists gets used):
  GROQ_API_KEY
  GROQ_MODEL            default: llama-3.3-70b-versatile
  GEMINI_API_KEY
  GEMINI_MODEL          default: gemini-2.0-flash
  HUGGINGFACE_API_KEY
  HUGGINGFACE_MODEL     default: meta-llama/Llama-3.1-8B-Instruct
"""

import os
import logging
import httpx

logger = logging.getLogger("uvicorn.error")

MAX_OUTPUT_TOKENS = 800
REQUEST_TIMEOUT = 30.0

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
HF_URL = "https://router.huggingface.co/v1/chat/completions"


class AIProviderError(Exception):
    """Raised when every configured provider failed."""


def _grok_system_to_messages(system_prompt, user_and_assistant):
    """Groq and HuggingFace use the OpenAI 'messages' format."""
    messages = [{"role": "system", "content": system_prompt}]
    for turn in user_and_assistant:
        messages.append({"role": turn["role"], "content": turn["parts"][0]["text"]})
    return messages


async def _try_groq(system_prompt, turns):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": _grok_system_to_messages(system_prompt, turns),
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.6,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        res = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"].strip()
    logger.warning("Groq failed (%s): %s", res.status_code, res.text[:200])
    return None


async def _try_gemini(system_prompt, turns):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    payload = {
        "contents": turns,
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS},
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        res = await client.post(
            GEMINI_URL.format(model=model), params={"key": api_key}, json=payload
        )
    if res.status_code == 200:
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    logger.warning("Gemini failed (%s): %s", res.status_code, res.text[:200])
    return None


async def _try_huggingface(system_prompt, turns):
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return None
    payload = {
        "model": os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
        "messages": _grok_system_to_messages(system_prompt, turns),
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        res = await client.post(
            HF_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
    if res.status_code == 200:
        body = res.json()
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() or None
    logger.warning("HuggingFace failed (%s): %s", res.status_code, res.text[:200])
    return None


async def get_ai_reply(system_prompt: str, turns: list) -> str:
    """
    Get a chat completion, trying every configured provider in turn.
    `turns` is Gemini format: [{"role": "user"|"model", "parts": [{"text": ...}]}]

    Raises AIProviderError if all providers are missing or failed.
    """
    providers = (
        _try_groq,
        _try_gemini,
        _try_huggingface,
    )
    last_error = None
    for provider in providers:
        try:
            reply = await provider(system_prompt, turns)
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            last_error = e
            logger.warning("%s unreachable: %s", provider.__name__, e)
            continue
        if reply:
            return reply
    raise AIProviderError(
        "No AI provider succeeded. Configure GROQ_API_KEY / GEMINI_API_KEY / "
        f"HUGGINGFACE_API_KEY. Last error: {last_error}"
    )
