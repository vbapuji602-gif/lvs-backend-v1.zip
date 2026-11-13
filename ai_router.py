"""
Multi-provider AI chat router: tries Gemini first, then Groq, then
OpenRouter, in that order, and reports which provider actually answered
instead of silently pretending every provider is a different "brand" of
AI. Each provider call uses its real REST API with the real key from
BackendConfig; a provider with no key configured is skipped.
"""
import time
from typing import List, Dict, Any, Optional

import httpx

from ..config import BackendConfig


class AiRouterError(Exception):
    pass


async def _call_gemini(prompt: str, system_instruction: str, api_key: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise AiRouterError("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise AiRouterError("Gemini returned empty text")
        return text


async def _call_openai_compatible(
    prompt: str, system_instruction: str, api_key: str, base_url: str, model: str
) -> str:
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise AiRouterError("Provider returned no choices")
        text = choices[0].get("message", {}).get("content", "")
        if not text:
            raise AiRouterError("Provider returned empty text")
        return text


async def _call_groq(prompt: str, system_instruction: str, api_key: str) -> str:
    return await _call_openai_compatible(
        prompt, system_instruction, api_key,
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
    )


async def _call_openrouter(prompt: str, system_instruction: str, api_key: str) -> str:
    return await _call_openai_compatible(
        prompt, system_instruction, api_key,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
    )


def _offline_fallback(prompt: str) -> str:
    lower = prompt.lower()
    if "time" in lower:
        return "Boss, I can't reach any AI provider right now (no network or no keys configured)."
    return (
        "Boss, none of the configured AI providers answered right now "
        "(check your API keys / network). Your message was noted: " + prompt[:200]
    )


async def route_chat(prompt: str, system_instruction: str = "You are LVS, a helpful bilingual Telugu/English voice assistant.") -> Dict[str, Any]:
    """
    Tries providers in order and returns the first successful reply along
    with which provider actually produced it, plus which ones were tried
    and failed. Nothing here fakes a provider that wasn't actually called.
    """
    attempts: List[Dict[str, str]] = []
    start = time.time()

    providers = []
    if BackendConfig.GEMINI_API_KEY:
        providers.append(("gemini", lambda: _call_gemini(prompt, system_instruction, BackendConfig.GEMINI_API_KEY)))
    if BackendConfig.GROQ_API_KEY:
        providers.append(("groq", lambda: _call_groq(prompt, system_instruction, BackendConfig.GROQ_API_KEY)))
    if BackendConfig.OPENROUTER_API_KEY:
        providers.append(("openrouter", lambda: _call_openrouter(prompt, system_instruction, BackendConfig.OPENROUTER_API_KEY)))

    for name, call in providers:
        try:
            text = await call()
            return {
                "text": text,
                "provider": name,
                "was_fallback": False,
                "failed_providers": attempts,
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            attempts.append({"provider": name, "error": str(e)[:300]})

    # Every configured provider failed, or none were configured.
    return {
        "text": _offline_fallback(prompt),
        "provider": "offline-fallback",
        "was_fallback": True,
        "failed_providers": attempts,
        "latency_ms": int((time.time() - start) * 1000),
    }
