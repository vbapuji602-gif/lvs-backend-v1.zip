import hashlib
import hmac
import time
from typing import Dict, Optional, Tuple

class AuthService:
    """Manages secure password verification, rate limiting, and session security."""

    def __init__(self, secret_key: str = "lvs-secure-backend-master-secret-key-32"):
        self.secret_key = secret_key.encode('utf-8')
        # Store failed attempts: {identifier: (attempt_count, lockout_until_timestamp)}
        self._failed_attempts: Dict[str, Tuple[int, float]] = {}

    def is_locked_out(self, identifier: str) -> bool:
        if identifier in self._failed_attempts:
            count, lockout_until = self._failed_attempts[identifier]
            if time.time() < lockout_until:
                return True
            elif time.time() >= lockout_until and count >= 5:
                # Lockout expired, reset
                del self._failed_attempts[identifier]
        return False

    def record_failed_attempt(self, identifier: str) -> int:
        current_time = time.time()
        count, _ = self._failed_attempts.get(identifier, (0, 0.0))
        new_count = count + 1
        lockout_until = 0.0
        if new_count >= 5:
            lockout_until = current_time + (15 * 60) # 15 minute lockout
        self._failed_attempts[identifier] = (new_count, lockout_until)
        return new_count

    def reset_failed_attempts(self, identifier: str) -> None:
        if identifier in self._failed_attempts:
            del self._failed_attempts[identifier]

    @classmethod
    def hash_password(cls, password: str, salt: str) -> str:
        salted = f"{salt}:{password}".encode('utf-8')
        return hashlib.sha256(salted).hexdigest()

    @classmethod
    def verify_password(cls, password: str, salt: str, expected_hash: str) -> bool:
        computed = cls.hash_password(password, salt)
        return hmac.compare_digest(computed, expected_hash)
