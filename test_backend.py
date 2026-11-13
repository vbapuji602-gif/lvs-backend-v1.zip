import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.auth_service import AuthService
from app.services.device_service import DeviceService
from app.models.schemas import DeviceRegistrationRequest
from app.main import LvsBackendApp

class TestBackend(unittest.TestCase):

    def setUp(self):
        self.auth_service = AuthService()
        self.device_service = DeviceService()
        self.backend = LvsBackendApp()

    def test_health_check(self):
        health = self.backend.health_check()
        self.assertEqual(health["status"], "healthy")
        self.assertIn("LVS", health["service"])

    def test_password_hashing_and_verification(self):
        salt = "random_salt_123"
        pwd = "LvsMasterPassword!2026"
        pwd_hash = AuthService.hash_password(pwd, salt)

        self.assertTrue(AuthService.verify_password(pwd, salt, pwd_hash))
        self.assertFalse(AuthService.verify_password("wrong_password", salt, pwd_hash))

    def test_brute_force_lockout_mechanism(self):
        user_id = "user_victim_999"
        self.assertFalse(self.auth_service.is_locked_out(user_id))

        # Fail 4 times
        for _ in range(4):
            self.auth_service.record_failed_attempt(user_id)
            self.assertFalse(self.auth_service.is_locked_out(user_id))

        # 5th failure triggers lockout
        self.auth_service.record_failed_attempt(user_id)
        self.assertTrue(self.auth_service.is_locked_out(user_id))

        # Resetting unlocks
        self.auth_service.reset_failed_attempts(user_id)
        self.assertFalse(self.auth_service.is_locked_out(user_id))

    def test_device_registration_and_revocation(self):
        req = DeviceRegistrationRequest(
            device_id="pixel-7-user1",
            user_id="user_alice",
            device_name="Alice's Pixel 7",
            model="Pixel 7",
            battery_pct=82,
            is_charging=True,
            network_state="Wi-Fi"
        )
        record = self.device_service.register_or_update_device(req)
        self.assertEqual(record.device_id, "pixel-7-user1")
        self.assertEqual(record.battery_pct, 82)

        devices = self.device_service.get_user_devices("user_alice")
        self.assertEqual(len(devices), 1)

        # Revocation
        revoked = self.device_service.revoke_device("user_alice", "pixel-7-user1")
        self.assertTrue(revoked)
        devices_after = self.device_service.get_user_devices("user_alice")
        self.assertEqual(len(devices_after), 0)

if __name__ == '__main__':
    unittest.main()
