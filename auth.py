"""
Auth endpoints: first-time family setup, login, and 2FA elevation.

Flow matches what was asked for:
1. POST /auth/setup       - first device for a family creates the master password
2. POST /auth/login       - any family member logs in with the master password
3. POST /auth/setup-2fa   - (while logged in) sets the second "backend" password
4. POST /auth/elevate     - enter the second password to unlock sensitive actions
"""
import os
import secrets as pysecrets

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..services.auth_service import AuthService
from ..services.secrets_store import SecretsStore
from ..dependencies import require_session, get_session_service

router = APIRouter(prefix="/auth", tags=["Auth"])

_store = SecretsStore()
_auth = AuthService()


class SetupRequest(BaseModel):
    family_id: str
    password: str
    device_id: str
    device_name: str = "Device"


class LoginRequest(BaseModel):
    family_id: str
    password: str
    device_id: str
    device_name: str = "Device"


class Setup2faRequest(BaseModel):
    backend_password: str


class ElevateRequest(BaseModel):
    backend_password: str


@router.post("/setup")
def setup_family(req: SetupRequest):
    if _store.has_master_password(req.family_id):
        raise HTTPException(status_code=409, detail="This family already has a password. Use /auth/login instead.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    salt = pysecrets.token_hex(16)
    pwd_hash = AuthService.hash_password(req.password, salt)
    _store.set_master_password(req.family_id, salt, pwd_hash)

    session_service = get_session_service()
    token = session_service.create_token(req.family_id, req.device_id, scope="standard")
    return {"token": token, "scope": "standard", "message": "Family password set. Save this family_id to invite others."}


@router.post("/login")
def login(req: LoginRequest):
    identifier = f"{req.family_id}"
    if _auth.is_locked_out(identifier):
        raise HTTPException(status_code=423, detail="Too many failed attempts. Try again in 15 minutes.")

    record = _store.get_master_password(req.family_id)
    if not record:
        raise HTTPException(status_code=404, detail="Unknown family_id. Use /auth/setup first.")

    if not AuthService.verify_password(req.password, record["salt"], record["hash"]):
        attempts = _auth.record_failed_attempt(identifier)
        raise HTTPException(status_code=401, detail=f"Wrong password ({attempts}/5 attempts before lockout).")

    _auth.reset_failed_attempts(identifier)
    session_service = get_session_service()
    token = session_service.create_token(req.family_id, req.device_id, scope="standard")
    return {"token": token, "scope": "standard"}


@router.post("/setup-2fa")
def setup_2fa(req: Setup2faRequest, session=Depends(require_session)):
    if len(req.backend_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    salt = pysecrets.token_hex(16)
    pwd_hash = AuthService.hash_password(req.backend_password, salt)
    _store.set_backend_password(session["family_id"], salt, pwd_hash)
    return {"message": "Second security password set."}


@router.post("/elevate")
def elevate(req: ElevateRequest, session=Depends(require_session)):
    family_id = session["family_id"]
    identifier = f"{family_id}:2fa"
    if _auth.is_locked_out(identifier):
        raise HTTPException(status_code=423, detail="Too many failed attempts. Try again in 15 minutes.")

    record = _store.get_backend_password(family_id)
    if not record:
        raise HTTPException(status_code=404, detail="No second password set yet. Call /auth/setup-2fa first.")

    if not AuthService.verify_password(req.backend_password, record["salt"], record["hash"]):
        attempts = _auth.record_failed_attempt(identifier)
        raise HTTPException(status_code=401, detail=f"Wrong second password ({attempts}/5 attempts before lockout).")

    _auth.reset_failed_attempts(identifier)
    session_service = get_session_service()
    token = session_service.create_token(family_id, session["device_id"], scope="elevated", expire_minutes=15)
    return {"token": token, "scope": "elevated", "expires_in_minutes": 15}
