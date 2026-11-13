from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import time

@dataclass
class UserLoginRequest:
    email: str
    password_hash: str
    device_id: str
    device_name: str

@dataclass
class DeviceRegistrationRequest:
    device_id: str
    user_id: str
    device_name: str
    model: str = "Android"
    battery_pct: int = 100
    is_charging: bool = False
    network_state: str = "Online"

@dataclass
class DeviceRecord:
    device_id: str
    user_id: str
    device_name: str
    model: str
    battery_pct: int
    is_charging: bool
    network_state: str
    is_online: bool = True
    last_seen: float = field(default_factory=time.time)

@dataclass
class SyncBatchRequest:
    device_id: str
    user_id: str
    items: List[Dict[str, Any]] = field(default_factory=list)
