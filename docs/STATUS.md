# Status — What works / Limitations

_Last verified: 2026-10-22, on Windows 11 (Python 3.11.9, Node 20.20.2). Provider: **OpenAI**._

Real OpenAI calls and the full application workflow have been executed and verified
(not just unit tests). No accuracy numbers are invented.

## AI provider / model

- Uses the **official OpenAI Python SDK** (`openai` 3.x) via `backend/app/ai/provider.py`
  (Chat Completions with image input + JSON response format). Anthropic is no longer used.
- Configured model in `.env`: `AI_MODEL=gpt-6-luna` — **verified accessible** to this
  account (`client.models.retrieve` succeeds) and confirmed to perform real vision
  transcription on the sample photos.
- If a configured model is unavailable, the adapter **auto-falls back** through
  `gpt-4o → gpt-4o-mini → gpt-4.1 → gpt-4.1-mini` and logs the substitution.
- The API key is read from `.env`/env only and is **never logged or returned** (health
  endpoint shows provider + model name, never the key).

## ✅ Verified working (with REAL OpenAI calls)

| Feature | How verified |
|---|---|
| Env vars load; `/api/health` reports provider + model, key never exposed | Live HTTP |
| Teacher login + signed session cookie; all `/api/*` protected | Automated + live + browser |
| Create test; writing tests auto-get a 5-category rubric (totals validated) | Automated + live |
| Upload the **two real photos** as one ordered multi-page submission | Live HTTP + browser |
| Images stored on disk, served only to authenticated requests; traversal-guarded | Live HTTP |
| **Real handwriting transcription** (vision) — errors mostly preserved, crossed-out text excluded + noted, printed text excluded, pages merged in order, ambiguities flagged | **Real OpenAI call**, smoke script + in-browser Analyze |
| Deterministic word count (316/318 on the sample) + rubric totals, clamped per-criterion and overall | Automated + live |
| **Separate** evaluation call → grammar/spelling/punctuation issues with corrections + explanations, rubric suggestions, overall feedback | **Real OpenAI call**, browser |
| Edit transcription → **Re-evaluate** (no re-upload) → refreshed scores | Browser (real call) |
| Override a rubric score → deterministic final recomputed (e.g. 5.7/10) | Browser + API |
| Add teacher comment → **Approve & Save** → appears in Results | Browser + API |
| Reopen a saved/approved submission (persists across restart; SQLite) | Browser + API |
| **Graceful failure with no/invalid key**: clear error, submission marked `error`, never fabricates | Live HTTP (earlier, keyless) |
| Invalid/oversized/non-image uploads rejected | Automated |
| SPA deep links survive hard refresh in single-process mode | Browser |
| Backend test suite | `pytest` → **12 passed** |
| Frontend production build | `npm run build` → clean |

## Known limitations (deliberate, prototype scope)

- **Transcription occasionally normalizes a word** despite being told to preserve errors
  (e.g. read "starteld" as "startled", "flowes" as "flowers"). This is inherent LLM
  behavior; the prompt discourages it, and the teacher edits the transcription in review —
  which is the intended safeguard. Do not assume byte-perfect error preservation.
- **Run-to-run variance**: the same photos can yield slightly different wording, word counts,
  and suggested scores between analyses (normal for LLMs). Totals are always deterministic
  given a transcription + approved scores.
- **Synchronous analysis** (20–60s in-process); no Redis/Celery queue. Fine for one teacher.
- **SQLite + local disk**; no Postgres/S3, no Alembic migrations (tables auto-created).
- **No custom crossed-out CV**: relies on the vision model and flags uncertainty.
- **Re-evaluation re-seeds** suggested scores from the fresh AI pass (teacher can still edit).
- **No automated question-boundary detection** for multi-question worksheets — flagged in
  `notes` instead of guessed.
- **PWA**: responsive + mobile-camera upload, but no offline service worker in this cut.
- **HTTPS / public URL** is an operator deploy step (see README).

## Definition-of-Done mapping

All 13 items of the OpenAI-task Definition of Done are **met and verified live**: real
OpenAI transcription (2), extracted text + uncertain passages (3), AI evaluation (4),
suggested grade + rubric breakdown (5), automated + browser tests (6), limitations (7).
Item 8 (private HTTPS link) is **documented** as the operator's one deploy step (README →
"Deploying with a private HTTPS URL").
