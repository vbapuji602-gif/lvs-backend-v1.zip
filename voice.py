import base64

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..providers.voice_service import synthesize_speech, VoiceServiceError
from ..dependencies import require_session

router = APIRouter(prefix="/voice", tags=["Voice"])


class TtsRequest(BaseModel):
    text: str
    voice_id: str | None = None


@router.post("/tts")
async def text_to_speech(req: TtsRequest, session=Depends(require_session)):
    try:
        audio_bytes = await synthesize_speech(req.text, req.voice_id)
    except VoiceServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"audio_base64": base64.b64encode(audio_bytes).decode("utf-8"), "format": "mp3"}
