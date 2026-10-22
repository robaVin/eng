# English Test Grading — Prototype

A small, private web app that helps **one English teacher** grade handwritten paper
exams faster. The teacher configures a test, uploads phone photos of a student's
handwritten work, clicks **Analyze**, and gets:

- an AI transcription of the handwriting (student mistakes preserved, crossed-out text excluded),
- flagged spelling / grammar / punctuation issues with suggested corrections,
- rubric-based suggested scores,
- a review screen to **edit the transcription, re-evaluate, override scores, and approve**.

The teacher is always the final authority. AI output is a suggestion; nothing is finalized
until the teacher approves it.

> This is a **private development prototype**, not production SaaS. See **Limitations** below.

---

## Architecture (small on purpose)

```
React + Vite + TS + Tailwind   ─HTTP(cookie session)─▶   FastAPI (single process)
  3 screens + login gate                                   ├─ SQLite (tests, submissions, results)
                                                            ├─ local disk (uploaded images)
                                                            └─ AI adapter → OpenAI (vision)
                                                                 step 1: transcribe (never corrects)
                                                                 step 2: evaluate  (never invents text)
```

- **Two separate AI operations.** Transcription and evaluation are different calls with
  different prompts. The transcription model is told never to fix the student's English;
  the evaluation model is told never to invent unreadable text.
- **Deterministic grading.** Word counts and score totals are computed in Python
  (`backend/app/grading.py`), never taken from the AI.

Full phased architecture lives in [docs/ROADMAP.md](docs/ROADMAP.md). Real handwriting
fixtures + a verified reference transcription are in [test-data/](test-data/).

---

## Prerequisites

- Python 3.11+
- Node 20+
- An OpenAI API key (for real analysis)

## 1) Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate       macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env (set OPENAI_API_KEY, TEACHER_PASSWORD, SECRET_KEY)
uvicorn app.main:app --reload --port 8000
```

The backend creates `backend/data/app.db` and `backend/data/uploads/` on first run.

## 2) Frontend (dev)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to the backend on :8000)
```

Open http://localhost:5173, log in with `TEACHER_PASSWORD`, and use the three screens:
**Test Setup → Upload Work → Review**.

## 3) Production (single process)

Build the frontend; FastAPI will serve it at the same origin as the API:

```bash
cd frontend && npm run build        # outputs frontend/dist
cd ../backend && uvicorn app.main:app --port 8000
```

Now everything is on http://localhost:8000 (no separate frontend server).

---

## Environment variables (`backend/.env`)

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI key (server-side only; never in frontend) | — (required for analysis) |
| `AI_PROVIDER` | AI provider (only `openai` implemented) | `openai` |
| `AI_MODEL` | Vision-capable model id; auto-falls back if unavailable | `gpt-4o` |
| `TEACHER_PASSWORD` | The single login password | `changeme` |
| `SECRET_KEY` | Signs the session cookie — use a long random string | insecure default |
| `DATA_DIR` | Where SQLite + uploads live | `./data` |
| `COOKIE_SECURE` | `1` when served over HTTPS (marks cookie Secure) | `0` |
| `MAX_UPLOAD_MB` | Per-image size limit | `15` |

---

## Testing

```bash
cd backend
.venv/Scripts/python -m pytest        # (Windows path; use .venv/bin/python elsewhere)
```

Covers deterministic grading (word count, rubric totals, score clamping) and the full
API workflow (upload → analyze → re-evaluate → review → reopen) with the **AI mocked**.

---

## Deploying with a private HTTPS URL

For a tester on their own device, the simplest safe option is a tunnel in front of the
single-process server (step 3), which gives you HTTPS automatically:

```bash
# with the app running on :8000
cloudflared tunnel --url http://localhost:8000      # or: ngrok http 8000
```

Then set `COOKIE_SECURE=1` in `.env` and restart. Access is still gated by the password.
This tunnel step is performed by the teacher/operator; it is not run automatically.

---

## What works / Limitations

See [docs/STATUS.md](docs/STATUS.md) for the verified "what works" list and the honest
list of limitations and what has / hasn't been live-tested.
