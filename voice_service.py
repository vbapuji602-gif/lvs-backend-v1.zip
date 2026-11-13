"""
ElevenLabs text-to-speech. Returns raw MP3 bytes; the router layer
base64-encodes them for the mobile client, since JSON can't carry
binary directly.
"""
import httpx

from ..config import BackendConfig


class VoiceServiceError(Exception):
    pass


async def synthesize_speech(text: str, voice_id: str = None) -> bytes:
    if not BackendConfig.ELEVENLABS_API_KEY:
        raise VoiceServiceError("ELEVENLABS_API_KEY is not configured on the backend")

    vid = voice_id or BackendConfig.ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {
        "xi-api-key": BackendConfig.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code != 200:
            raise VoiceServiceError(f"ElevenLabs error {resp.status_code}: {resp.text[:300]}")
        return resp.content
