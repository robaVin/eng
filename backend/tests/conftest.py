"""Pytest fixtures: isolated temp data dir + an authenticated TestClient with AI mocked."""
from __future__ import annotations

import io
import os
import tempfile

# Must configure settings BEFORE importing the app (settings is read at import time).
_TMP = tempfile.mkdtemp(prefix="eng_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["TEACHER_PASSWORD"] = "test-pass"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["OPENAI_API_KEY"] = "test-key-not-used"  # mocked; no real calls

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.ai import provider  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import EvaluationResult, TranscriptionResult  # noqa: E402

# TestClient(app) without a `with` block does not fire startup events, so create
# the tables explicitly for the test session.
init_db()


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def png() -> bytes:
    return _png_bytes()


@pytest.fixture
def mock_ai(monkeypatch):
    """Replace the two AI operations with deterministic canned responses."""

    def fake_transcribe(images, *, test_title, instructions):
        return (
            TranscriptionResult(
                transcription="She answered the phone after the third ring. It was wierd.",
                uncertain_passages=["breathiy"],
                crossed_out_notes=["student crossed out 'fifth'"],
                pages=[{"page": 1, "summary": "handwriting begins after printed intro"}],
            ),
            {"input_tokens": 10, "output_tokens": 20, "model": "mock"},
        )

    def fake_evaluate(**kwargs):
        rubric = kwargs.get("rubric") or [{"name": "Overall", "points": kwargs["max_points"]}]
        scores = []
        for item in rubric:
            scores.append(
                {
                    "criterion": item["name"],
                    "max_points": item["points"],
                    "suggested_points": round(item["points"] * 0.8, 2),
                    "explanation": "mock",
                }
            )
        return (
            EvaluationResult(
                issues=[
                    {"type": "spelling", "original": "wierd", "correction": "weird", "explanation": "i before e"}
                ],
                rubric_scores=scores,
                overall_feedback="Good effort.",
                notes=[],
            ),
            {"input_tokens": 5, "output_tokens": 10, "model": "mock"},
        )

    monkeypatch.setattr(provider, "transcribe", fake_transcribe)
    monkeypatch.setattr(provider, "evaluate", fake_evaluate)


@pytest.fixture
def client():
    c = TestClient(app)
    # authenticate
    r = c.post("/api/login", json={"password": "test-pass"})
    assert r.status_code == 200
    return c
