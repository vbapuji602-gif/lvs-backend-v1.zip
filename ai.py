from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..providers.ai_router import route_chat
from ..dependencies import require_session

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    prompt: str
    system_instruction: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest, session=Depends(require_session)):
    kwargs = {}
    if req.system_instruction:
        kwargs["system_instruction"] = req.system_instruction
    result = await route_chat(req.prompt, **kwargs)
    return result
