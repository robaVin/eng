"""Login / logout / session status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth import login_session, logout_session, verify_password
from ..config import settings

router = APIRouter(prefix="/api", tags=["auth"])


class LoginIn(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginIn, request: Request):
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    login_session(request)
    return {"ok": True}


@router.post("/logout")
def logout(request: Request):
    logout_session(request)
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    return {
        "authenticated": bool(request.session.get("auth")),
        "ai_configured": settings.ai_configured,
    }
