"""Deterministic grading helpers.

Totals and word counts are computed here in Python — never taken from the AI —
so grades are reproducible and auditable.
"""
from __future__ import annotations

import re

from .schemas import RubricItem

# Default writing rubric categories (weights are distributed to match max_points).
DEFAULT_WRITING_CATEGORIES = [
    "Grammar",
    "Vocabulary",
    "Spelling & Punctuation",
    "Coherence & Organization",
    "Task Completion & Creativity",
]

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*")


def count_words(text: str | None) -> int:
    """Deterministic word count of the student's active composition.

    The transcription already excludes printed instructions and crossed-out text,
    so we simply count word-like tokens (contractions/hyphenated words count once).
    """
    if not text:
        return 0
    return len(_WORD_RE.findall(text))


def default_writing_rubric(max_points: float) -> list[RubricItem]:
    """Spread max_points across the default categories as evenly as possible."""
    n = len(DEFAULT_WRITING_CATEGORIES)
    base = round(max_points / n, 2)
    items = [RubricItem(name=c, points=base) for c in DEFAULT_WRITING_CATEGORIES]
    # fix rounding drift so the total matches exactly
    drift = round(max_points - base * n, 2)
    if drift and items:
        items[0].points = round(items[0].points + drift, 2)
    return items


def rubric_total(rubric: list[RubricItem] | list[dict] | None) -> float:
    if not rubric:
        return 0.0
    total = 0.0
    for item in rubric:
        pts = item.points if isinstance(item, RubricItem) else float(item.get("points", 0))
        total += pts
    return round(total, 2)


def rubric_matches_max(rubric: list[RubricItem] | None, max_points: float) -> bool:
    return abs(rubric_total(rubric) - float(max_points)) < 0.01


def compute_total(
    approved_scores: dict[str, float] | None,
    rubric: list[dict] | None,
    max_points: float,
) -> float:
    """Sum approved per-criterion points, clamping each to its rubric max and the
    overall total to the test's max_points. Never returns a negative total."""
    if not approved_scores:
        return 0.0
    caps = {}
    if rubric:
        for item in rubric:
            caps[item["name"]] = float(item.get("points", 0))
    total = 0.0
    for name, pts in approved_scores.items():
        try:
            val = float(pts)
        except (TypeError, ValueError):
            val = 0.0
        val = max(0.0, val)
        if name in caps:
            val = min(val, caps[name])
        total += val
    total = max(0.0, min(total, float(max_points)))
    return round(total, 2)


def suggested_scores_from_evaluation(evaluation: dict | None) -> dict[str, float]:
    """Pull the AI's suggested per-criterion points into an approved_scores-shaped dict
    (the teacher can then edit these before finalizing)."""
    out: dict[str, float] = {}
    if not evaluation:
        return out
    for rs in evaluation.get("rubric_scores", []) or []:
        name = rs.get("criterion")
        if name is not None:
            try:
                out[name] = float(rs.get("suggested_points", 0))
            except (TypeError, ValueError):
                out[name] = 0.0
    return out
