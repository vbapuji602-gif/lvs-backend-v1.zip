"""
Shared FastAPI dependencies: bearer-token session auth with two scopes.
"standard" = logged in with the master password.
"elevated" = also passed the second (backend/2FA) password; required for
sensitive actions like camera, screen share, or location history.
"""
from fastapi import Header, HTTPException

from .services.session_service import SessionService
from .config import BackendConfig

_session_service = SessionService(BackendConfig.SECRET_KEY or "lvs-dev-only-change-me")


def get_session_service() -> SessionService:
    return _session_service


def require_session(authorization: str = Header(default="")):
    """Requires any valid, non-expired session token (standard or elevated)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization[len("Bearer "):]
    payload = _session_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return payload


def require_elevated_session(authorization: str = Header(default="")):
    """Requires a session that has also passed the second (2FA) password."""
    payload = require_session(authorization)
    if payload.get("scope") != "elevated":
        raise HTTPException(
            status_code=403,
            detail="This action needs the second security password (2FA) first. Call /auth/elevate.",
        )
    return payload
