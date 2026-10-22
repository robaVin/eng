"""Live HTTP end-to-end check against a running server on :8000 using the REAL sample
images. Verifies auth, test config, multi-page upload, image serving, graceful AI-not-
configured handling, and review save/reopen/list. Does NOT require an AI key."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "test-data" / "handwriting-samples"
BASE = "http://127.0.0.1:8000"
PAGES = ["mysterious-letter_page-1.jpeg", "mysterious-letter_page-2.jpeg"]

ok = 0
fail = 0


def check(name: str, cond: bool, extra: str = ""):
    global ok, fail
    mark = "PASS" if cond else "FAIL"
    if cond:
        ok += 1
    else:
        fail += 1
    print(f"[{mark}] {name}{(' — ' + extra) if extra else ''}")


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=30)

    # wait for readiness
    for _ in range(20):
        try:
            if c.get("/api/health").status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        print("Server not reachable on :8000")
        return 1

    h = c.get("/api/health").json()
    check("health ok", h.get("status") == "ok", f"ai_configured={h.get('ai_configured')}")

    check("unauth blocked", c.get("/api/tests").status_code == 401)

    r = c.post("/api/login", json={"password": "test1234"})
    check("login", r.status_code == 200)

    r = c.post(
        "/api/tests",
        json={
            "title": "The Mysterious Letter", "test_type": "writing",
            "instructions": "Continue the story in 150-180 words.",
            "max_points": 10, "criteria": "Creative, logical, correct grammar.",
            "word_min": 150, "word_max": 180,
        },
    )
    check("create writing test", r.status_code == 200, r.text[:120])
    test = r.json()
    check("default rubric has 5 criteria totalling 10",
          len(test["rubric"]) == 5 and abs(sum(x["points"] for x in test["rubric"]) - 10) < 0.01)

    files = [("files", (p, (SAMPLES / p).read_bytes(), "image/jpeg")) for p in PAGES]
    r = c.post("/api/submissions", data={"student_name": "Emma", "test_id": test["id"]}, files=files)
    check("upload 2 real pages", r.status_code == 200, r.text[:120])
    sub = r.json()
    check("submission has 2 ordered pages", len(sub["image_paths"]) == 2)
    sid = sub["id"]

    r0 = c.get(f"/api/submissions/{sid}/pages/0")
    r1 = c.get(f"/api/submissions/{sid}/pages/1")
    check("page 0 served as image", r0.status_code == 200 and r0.headers["content-type"].startswith("image/"))
    check("page 1 served as image", r1.status_code == 200 and len(r1.content) > 1000)
    check("missing page 404", c.get(f"/api/submissions/{sid}/pages/5").status_code == 404)

    # No AI key here -> analyze must fail gracefully, never fabricate.
    r = c.post(f"/api/submissions/{sid}/analyze")
    check("analyze fails gracefully without key (503)", r.status_code == 503,
          r.json().get("detail", "")[:80])
    check("submission marked error, not fabricated",
          c.get(f"/api/submissions/{sid}").json()["status"] == "error")

    # Teacher review path works without AI (manual transcription + scores).
    r = c.patch(
        f"/api/submissions/{sid}/review",
        json={
            "corrected_transcription": "She answered the phone after the third ring. It was wierd.",
            "approved_scores": {x["name"]: x["points"] for x in test["rubric"]},
            "teacher_comments": "Strong effort; watch spelling.",
        },
    )
    check("save review -> approved", r.status_code == 200 and r.json()["status"] == "approved", r.text[:120])
    saved = r.json()
    check("final score = max when all criteria full", saved["final_score"] == 10, str(saved["final_score"]))
    check("deterministic word count computed", saved["word_count"] == 11, str(saved["word_count"]))

    # Reopen later
    reopened = c.get(f"/api/submissions/{sid}").json()
    check("reopen persists approval + comments",
          reopened["status"] == "approved" and reopened["teacher_comments"] == "Strong effort; watch spelling.")

    lst = c.get("/api/submissions").json()
    check("appears in results list", any(s["id"] == sid for s in lst))

    print(f"\n{ok} passed, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
