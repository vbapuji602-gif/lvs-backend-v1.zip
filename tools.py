from fastapi import APIRouter, Depends, HTTPException

from ..providers.tools_service import get_weather, get_crypto_price, ToolServiceError
from ..dependencies import require_session

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("/weather")
async def weather(location: str, session=Depends(require_session)):
    try:
        return await get_weather(location)
    except ToolServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/crypto")
async def crypto(coin_id: str = "bitcoin", vs_currency: str = "usd", session=Depends(require_session)):
    try:
        return await get_crypto_price(coin_id, vs_currency)
    except ToolServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
