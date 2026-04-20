"""
app/routers/voice.py
  POST /api/voice/tts     — synthesize text → MP3
  GET  /api/voice/voices  — list available Indian + English voices
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.models.schemas import TTSRequest
from app.services.tts_service import synthesize, list_voices

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    try:
        audio = await synthesize(req.text, req.voice)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc, exc_info=True)
        raise HTTPException(500, f"TTS failed: {exc}")
    return Response(content=audio, media_type="audio/mpeg")


@router.get("/voices")
async def get_voices():
    return {"voices": await list_voices()}
