"""
Lightweight signed session tokens (HMAC-SHA256, no external JWT dependency).
Format: base64(payload_json).base64(signature)
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any

from ..config import BackendConfig


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class SessionService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode("utf-8")

    def _sign(self, payload_b64: str) -> str:
        sig = hmac.new(self.secret_key, payload_b64.encode("utf-8"), hashlib.sha256).digest()
        return _b64e(sig)

    def create_token(self, family_id: str, device_id: str, scope: str = "standard",
                      expire_minutes: Optional[int] = None) -> str:
        expire_minutes = expire_minutes or BackendConfig.ACCESS_TOKEN_EXPIRE_MINUTES
        payload = {
            "family_id": family_id,
            "device_id": device_id,
            "scope": scope,  # "standard" or "elevated" (after 2FA)
            "exp": time.time() + expire_minutes * 60,
        }
        payload_b64 = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        sig_b64 = self._sign(payload_b64)
        return f"{payload_b64}.{sig_b64}"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload_b64, sig_b64 = token.split(".", 1)
        except ValueError:
            return None
        expected_sig = self._sign(payload_b64)
        if not hmac.compare_digest(expected_sig, sig_b64):
            return None
        try:
            payload = json.loads(_b64d(payload_b64))
        except Exception:
            return None
        if payload.get("exp", 0) < time.time():
            return None
        return payload
