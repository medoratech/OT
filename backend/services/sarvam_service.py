"""
Sarvam TTS service.
Converts text to speech using Sarvam AI API (Indian English / Hindi support).
"""
import httpx
import base64
from config import settings


async def synthesize_speech(
    text: str,
    language_code: str = "en-IN",
    speaker: str = "meera",
    speech_rate: float = 1.0,
) -> bytes:
    """
    Call Sarvam TTS API and return raw audio bytes (WAV/MP3).

    Returns:
        bytes: audio content
    Raises:
        httpx.HTTPStatusError on failure
    """
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": [text[:500]],  # Sarvam has per-request char limit
        "target_language_code": language_code,
        "speaker": speaker,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
        "model": "bulbul:v1",
        "pace": speech_rate,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.SARVAM_TTS_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    # Sarvam returns base64-encoded audio in `audios` list
    audio_b64 = data.get("audios", [""])[0]
    audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
    return audio_bytes
