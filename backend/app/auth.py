"""Minimal single-teacher authentication.

A single password (server-side, from env) gates access. On success we set a signed,
HttpOnly session cookie via Starlette's SessionMiddleware. There is no frontend-only
check: every protected route verifies the server-side session.
"""
from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, status

from .config import settings


def verify_password(candidate: str) -> bool:
    """Constant-time comparison against the configured teacher password."""
    expected = settings.teacher_password or ""
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def login_session(request: Request) -> None:
    request.session["auth"] = True


def logout_session(request: Request) -> None:
    request.session.clear()


def require_auth(request: Request) -> None:
    """FastAPI dependency: 401 unless the session is authenticated."""
    if not request.session.get("auth"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )


AuthDep = Depends(require_auth)
