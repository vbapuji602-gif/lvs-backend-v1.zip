"""
Persistent JSON-backed store for the master password and the second
"backend" (2FA) password. Never stores plaintext - only salt+hash pairs
produced by AuthService.hash_password.
"""
import json
import os
import threading
from typing import Optional, Dict, Any

from ..config import BackendConfig

_LOCK = threading.Lock()


class SecretsStore:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or BackendConfig.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.path = os.path.join(self.data_dir, "lvs_secrets.json")
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        with _LOCK:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
            os.replace(tmp, self.path)

    # ---- master password (first unlock layer) ----
    def has_master_password(self, family_id: str) -> bool:
        return family_id in self._data.get("master", {})

    def set_master_password(self, family_id: str, salt: str, pwd_hash: str):
        self._data.setdefault("master", {})[family_id] = {"salt": salt, "hash": pwd_hash}
        self._save()

    def get_master_password(self, family_id: str) -> Optional[Dict[str, str]]:
        return self._data.get("master", {}).get(family_id)

    # ---- second / backend password (2FA for sensitive actions) ----
    def has_backend_password(self, family_id: str) -> bool:
        return family_id in self._data.get("backend2fa", {})

    def set_backend_password(self, family_id: str, salt: str, pwd_hash: str):
        self._data.setdefault("backend2fa", {})[family_id] = {"salt": salt, "hash": pwd_hash}
        self._save()

    def get_backend_password(self, family_id: str) -> Optional[Dict[str, str]]:
        return self._data.get("backend2fa", {}).get(family_id)
