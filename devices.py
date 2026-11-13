from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.device_service import DeviceService
from ..dependencies import require_session, require_elevated_session

router = APIRouter(prefix="/devices", tags=["Devices"])

_device_service = DeviceService()


class DeviceHeartbeat(BaseModel):
    device_id: str
    device_name: str
    model: str = "Android"
    battery_pct: int = 100
    is_charging: bool = False
    network_state: str = "Online"


@router.post("/heartbeat")
def heartbeat(req: DeviceHeartbeat, session=Depends(require_session)):
    """Each device calls this periodically to report battery/network and stay listed as online."""
    from ..models.schemas import DeviceRegistrationRequest
    record = _device_service.register_or_update_device(
        DeviceRegistrationRequest(
            device_id=req.device_id,
            user_id=session["family_id"],
            device_name=req.device_name,
            model=req.model,
            battery_pct=req.battery_pct,
            is_charging=req.is_charging,
            network_state=req.network_state,
        )
    )
    return record


@router.get("")
def list_devices(session=Depends(require_session)):
    """Lists every device in the caller's family group."""
    return _device_service.get_user_devices(session["family_id"])


@router.delete("/{device_id}")
def revoke_device(device_id: str, session=Depends(require_elevated_session)):
    """Removes a device from the family group. Requires the second password
    since this revokes someone's access."""
    ok = _device_service.revoke_device(session["family_id"], device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"revoked": device_id}
