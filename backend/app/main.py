"""FastAPI application entrypoint for the single-teacher grading prototype."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .db import init_db
from .routers import auth as auth_router
from .routers import submissions as submissions_router
from .routers import tests as tests_router

app = FastAPI(title="English Test Grading — Prototype")

# Signed, HttpOnly session cookie (server-side auth check happens in require_auth).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.cookie_secure,
    same_site="lax",
)

# CORS for the Vite dev server (same-origin in production, so this is dev-only).
dev_origins = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in dev_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_configured,
        "ai_model_configured": settings.ai_model,
    }


app.include_router(auth_router.router)
app.include_router(tests_router.router)
app.include_router(submissions_router.router)

# Serve the built frontend if present (production single-process mode), with an SPA
# fallback: real asset files are served directly; any other non-API path returns
# index.html so client-side routes (e.g. /review/1) survive a hard refresh.
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    _index = _frontend_dist / "index.html"

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (_frontend_dist / full_path).resolve()
        if _frontend_dist.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_index)
