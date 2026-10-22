"""Real end-to-end AI smoke test against the two sample handwriting images, using the
app's actual OpenAI adapter. Costs real API calls. Run from backend/:

    .venv/Scripts/python scripts/smoke_ai.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "test-data" / "handwriting-samples"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app import grading  # noqa: E402
from app.ai import provider  # noqa: E402
from app.config import settings  # noqa: E402

PAGES = ["mysterious-letter_page-1.jpeg", "mysterious-letter_page-2.jpeg"]
TITLE = "The Mysterious Letter"
INSTRUCTIONS = "Continue the story in 150-180 words, with correct grammar and punctuation."


def main() -> int:
    missing = [p for p in PAGES if not (SAMPLES / p).exists()]
    if missing:
        print(f"Sample images missing: {missing}. Place them in {SAMPLES}.")
        return 2
    if not settings.ai_configured:
        print("OPENAI_API_KEY is not set in backend/.env — cannot run real AI test.")
        return 3

    images = [((SAMPLES / p).read_bytes(), "image/jpeg") for p in PAGES]

    print("=== STEP 1: TRANSCRIPTION (real OpenAI call) ===")
    try:
        tr, tr_usage = provider.transcribe(images, test_title=TITLE, instructions=INSTRUCTIONS)
    except provider.AIError as exc:
        print(f"Transcription failed: {exc}")
        return 4
    wc = grading.count_words(tr.transcription)
    print(f"[model: {provider.current_model()}]  tokens in/out: {tr_usage['input_tokens']}/{tr_usage['output_tokens']}\n")
    print(tr.transcription)
    print(f"\n-- deterministic word count: {wc}")
    print(f"-- uncertain passages: {tr.uncertain_passages}")
    print(f"-- crossed-out notes: {tr.crossed_out_notes}")
    print(f"-- page notes: {tr.pages}")

    print("\n=== STEP 2: EVALUATION (real OpenAI call) ===")
    rubric = [r.model_dump() for r in grading.default_writing_rubric(10)]
    try:
        ev, ev_usage = provider.evaluate(
            test_type="writing", title=TITLE, instructions=INSTRUCTIONS,
            criteria="Creative, logical, correct grammar and punctuation.", max_points=10,
            expected_answer=None, rubric=rubric, word_min=150, word_max=180,
            transcription=tr.transcription, word_count=wc,
        )
    except provider.AIError as exc:
        print(f"Evaluation failed: {exc}")
        return 5

    seeded = grading.suggested_scores_from_evaluation(ev.model_dump())
    total = grading.compute_total(seeded, rubric, 10)
    print(f"tokens in/out: {ev_usage['input_tokens']}/{ev_usage['output_tokens']}\n")
    print(json.dumps(ev.model_dump(), indent=2, ensure_ascii=False)[:5000])
    print(f"\n-- suggested rubric total (deterministic, capped at 10): {total}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
