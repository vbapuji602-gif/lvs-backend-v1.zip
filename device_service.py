from typing import Dict, List, Optional
import time
from ..models.schemas import DeviceRecord, DeviceRegistrationRequest

class DeviceService:
    """Manages registered devices, telemetry updates, and permission revocation."""

    def __init__(self):
        # In-memory device registry: {user_id: {device_id: DeviceRecord}}
        self._devices: Dict[str, Dict[str, DeviceRecord]] = {}

    def register_or_update_device(self, req: DeviceRegistrationRequest) -> DeviceRecord:
        if req.user_id not in self._devices:
            self._devices[req.user_id] = {}

        record = DeviceRecord(
            device_id=req.device_id,
            user_id=req.user_id,
            device_name=req.device_name,
            model=req.model,
            battery_pct=req.battery_pct,
            is_charging=req.is_charging,
            network_state=req.network_state,
            is_online=True,
            last_seen=time.time()
        )
        self._devices[req.user_id][req.device_id] = record
        return record

    def get_user_devices(self, user_id: str) -> List[DeviceRecord]:
        return list(self._devices.get(user_id, {}).values())

    def revoke_device(self, user_id: str, device_id: str) -> bool:
        if user_id in self._devices and device_id in self._devices[user_id]:
            del self._devices[user_id][device_id]
            return True
        return False
