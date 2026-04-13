"""
Deepgram ASR service.
Transcribes uploaded audio files using Deepgram Nova-2 Medical model.
"""
import httpx
from config import settings

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

DEEPGRAM_PARAMS = {
    "model": "nova-2-medical",
    "language": "en-IN",
    "smart_format": "true",
    "punctuate": "true",
    "diarize": "false",
    "utterances": "false",
}


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Send audio bytes to Deepgram and return transcript + metadata.

    Returns:
        {
            "transcript": str,
            "confidence": float,
            "words": int,
            "duration": float,
        }
    """
    headers = {
        "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
        "Content-Type": mime_type,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            DEEPGRAM_URL,
            headers=headers,
            params=DEEPGRAM_PARAMS,
            content=audio_bytes,
        )
        response.raise_for_status()
        data = response.json()

    try:
        channel = data["results"]["channels"][0]
        alt = channel["alternatives"][0]
        transcript = alt.get("transcript", "")
        confidence = alt.get("confidence", 0.0)
        words = len(alt.get("words", []))
        duration = data["metadata"].get("duration", 0.0)
    except (KeyError, IndexError):
        transcript = ""
        confidence = 0.0
        words = 0
        duration = 0.0

    return {
        "transcript": transcript,
        "confidence": round(confidence * 100, 1),
        "words": words,
        "duration": round(duration, 1),
    }
