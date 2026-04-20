"""
app/services/tts_service.py
Free TTS via edge-tts (Microsoft Edge neural voices).

Fallback chain:
  1. Requested voice (or TTS_VOICE from .env)
  2. hi-IN-SwaraNeural  (Hindi Female)
  3. hi-IN-MadhurNeural (Hindi Male)
  4. en-IN-NeerjaNeural (Indian English Female)
  5. en-US-JennyNeural  (US English — always works)
"""

from __future__ import annotations
import io
import logging
from typing import Optional

import edge_tts

from app.core.config import settings

logger = logging.getLogger(__name__)

VOICE_OPTIONS = [
    {"short_name": "hi-IN-SwaraNeural",   "friendly_name": "Swara (Hindi, Female)",       "locale": "hi-IN", "gender": "Female"},
    {"short_name": "hi-IN-MadhurNeural",  "friendly_name": "Madhur (Hindi, Male)",         "locale": "hi-IN", "gender": "Male"},
    {"short_name": "en-IN-NeerjaNeural",  "friendly_name": "Neerja (English-IN, Female)",  "locale": "en-IN", "gender": "Female"},
    {"short_name": "en-IN-PrabhatNeural", "friendly_name": "Prabhat (English-IN, Male)",   "locale": "en-IN", "gender": "Male"},
    {"short_name": "en-US-JennyNeural",   "friendly_name": "Jenny (English-US, Female)",   "locale": "en-US", "gender": "Female"},
]

# Fallback order — last entry always works
_VOICE_FALLBACKS = [
    "hi-IN-SwaraNeural",
    "hi-IN-MadhurNeural",
    "en-IN-NeerjaNeural",
    "en-US-JennyNeural",
]


async def _try_synthesize(text: str, voice: str) -> bytes:
    """Attempt synthesis with a single voice. Returns bytes or raises."""
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    audio = buf.getvalue()
    if not audio:
        raise RuntimeError(f"edge-tts returned empty audio for voice={voice}")
    return audio


async def synthesize(text: str, voice: Optional[str] = None) -> bytes:
    """
    Convert text → MP3 bytes.
    Tries requested voice first, then falls through the fallback chain.
    Never raises to the caller — returns English audio at worst.
    """
    text = text.strip()
    if not text:
        raise ValueError("Cannot synthesize empty text.")

    # Build ordered list: requested → default → fallbacks
    primary = voice or settings.TTS_VOICE
    chain = [primary] + [v for v in _VOICE_FALLBACKS if v != primary]

    last_exc = None
    for v in chain:
        try:
            audio = await _try_synthesize(text, v)
            if v != primary:
                logger.warning("TTS: primary voice %s failed, used fallback %s", primary, v)
            else:
                logger.info("TTS: %d chars → %d bytes  voice=%s", len(text), len(audio), v)
            return audio
        except Exception as exc:
            logger.warning("TTS voice %s failed: %s", v, exc)
            last_exc = exc
            continue

    raise RuntimeError(f"All TTS voices failed. Last error: {last_exc}")


async def list_voices() -> list[dict]:
    return VOICE_OPTIONS
