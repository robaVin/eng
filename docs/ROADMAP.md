# English Test Grading — Architecture & Implementation Roadmap

**Status:** Phase 0 (assessment) complete. Awaiting review before Phase 1.
**Date:** 2026-10-22

---

## 1. Repository assessment

- **Working dir:** `C:\york\eng` — **empty**, not a git repository. This is a **greenfield** build; no existing code, conventions, or dependencies to preserve.
- **Reference images:** The two "Mysterious Letter" handwriting photos exist and are now committed as fixtures under `test-data/handwriting-samples/` with a manually verified `reference-transcription.md`. Feasibility can be validated against real data from day one.
- **Implication:** No technical debt and no migration constraints. We adopt the recommended stack as-is.

## 2. Proposed architecture

A **modular monolith**: one FastAPI backend (clear internal service boundaries, no microservices), one React SPA/PWA frontend, PostgreSQL, Redis + worker for durable background processing, and S3-compatible object storage. All AI calls originate **server-side** through provider-independent adapters. Teacher is always the final authority; AI output is never auto-finalized.

```
[ React PWA ]  --HTTPS/JSON-->  [ FastAPI API ]  --enqueue-->  [ Redis ]  -->  [ Worker ]
     |                               |   |                                        |
   camera                        Postgres  S3 (images/crops/reports)        AI adapters
                                                                        (vision OCR, grading)
```

Processing state and review state are tracked **independently** (a submission can be `Completed` processing but `Awaiting review`).

## 3. Project structure

```
eng/
  backend/
    app/
      api/            # FastAPI routers (thin)
      core/           # config, security, logging
      db/             # SQLAlchemy models, session, Alembic migrations
      schemas/        # Pydantic request/response + AI structured outputs
      services/       # business logic per module (test, submission, grading, review...)
      imaging/        # OpenCV/Pillow: boundary detect, perspective, alignment, crop
      recognition/    # transcription orchestration (crossouts, insertions, merge)
      grading/        # deterministic matchers + rubric scorers + AI grading strategies
      ai/             # provider-independent adapters (vision, semantic, writing, keygen)
      workers/        # queue consumers, job orchestration
    tests/            # unit + integration (AI mocked)
    alembic/
  frontend/
    src/
      pages/          # Dashboard, Tests, Students, Submissions, Review, Results, Settings
      components/      features/      lib/ (api client, query hooks)  routes/
  prototype/          # Phase 1 handwriting feasibility harness (standalone)
  test-data/          # fixtures (already populated)
  docs/
  infra/              # Dockerfile(s), docker-compose, nginx, env templates
```

Rule: no god-files; each service/module independently testable. No speculative abstraction layers.

## 4. Database schema overview

Normalized PostgreSQL. Core entities and key relationships:

- **Teacher** (single user for MVP) — auth + preferences.
- **Student** — `id` UUID (stable key; **never** keyed by name), name, optional group. Unique constraint prevents accidental merges; same name is allowed, same identity is not.
- **Test** → **TestTemplateVersion** (versioned; approved versions are immutable for grading) → **TemplatePage** → **AnswerRegion** (template-relative coords, region type, page ref) and **Question** (type, section, instructions, max points, answer key, accepted alternatives, spelling/case policy, partial-credit rules, rubric). A question may own multiple regions.
- **Submission** (student + template version + processing status) → **SubmissionPage** (original image, order, quality state, alignment metadata) → **ExtractedAnswer** (question ref, crop ref, raw transcription, corrected transcription, recognition state) and **Composition** (multi-page writing: combined transcription, word count, page refs).
- **Evaluation** (suggested score, grading method, explanation, rubric version, **final score**, review state) → **RubricScore** (criterion, suggested pts, approved pts) and **WritingIssue** (span, category, explanation, suggested correction, review decision).
- **GradeRevision** (append-only audit: previous → new, timestamp, reason) — approved grades are never overwritten.
- **ProcessingJob** (type, status, attempts, error, timestamps) for retryable durable jobs.
- **ExportRecord** (report metadata).

Guarantees: foreign keys, unique constraints, indexes on hot paths, transactional writes, Alembic migrations, append-only grade history.

## 5. Frontend component structure

React + TypeScript + Vite + Tailwind + shadcn/ui + React Router + TanStack Query + React Hook Form + Zod. Seven sections: **Dashboard, Tests, Students, Submissions, Review, Results, Settings**. The centerpiece is the **Review workspace**: a three-panel desktop layout (original image w/ zoom+pan+region highlight | editable transcription + question/answer context | suggested score + errors + overrides + approve), plus a dedicated **Writing review mode** for continuous multi-page essays. Mobile is optimized for the **capture** flow (camera, retake, page ordering, upload progress). PWA manifest + installability.

## 6. Backend service structure

Service modules mirror the brief: **auth, test-management, document-capture, document-recognition, handwriting-transcription, grading, review, reporting**. Routers stay thin; services hold logic; imaging/recognition/grading/ai are libraries the services call. Every module is independently unit-testable with AI mocked.

## 7. Recognition pipeline design (two pipelines)

- **Pipeline A — fixed regions** (grammar/vocab/reading/short answer): detect doc boundary → perspective-correct → match template page → transform region coords → crop → transcribe crop → evaluate. The layout is known; we never re-ask AI to rediscover it.
- **Pipeline B — long-form composition** (essays/creative): identify writing task → determine member pages → extract handwriting regions → separate printed from handwritten → resolve reading order across pages → detect crossouts/insertions → build combined transcription → flag uncertainty → deterministic word count → evaluate against rubric.

Alignment stores metadata so extraction is inspectable/reproducible; on alignment failure the page is flagged for recapture/manual fix rather than trusted.

## 8. Grading engine architecture

Type-specific strategies, **not** one universal prompt:
- **Grammar / Vocabulary:** deterministic matching first (exact answer, accepted alternatives, spelling/case policy, partial credit). AI only when interpretation is genuinely required.
- **Reading comprehension:** rubric-based semantic evaluation (question + passage context + expected answer + alternatives + student answer + criteria) returning suggested score, explanation, matched/missing criteria, review recommendation.
- **Writing:** rubric evaluation across configurable weighted categories (task completion, creativity, coherence, organization, grammar, vocabulary, spelling, punctuation, word-count compliance). **Totals are always computed deterministically in the backend**, never taken from the AI. All writing grades require teacher approval.

## 9. AI integration approach

Provider-independent adapters for (1) vision handwriting recognition, (2) reading-comprehension evaluation, (3) writing analysis, (4) optional answer-key suggestion. Backend-only; credentials never in frontend. Structured outputs validated with Pydantic; retries, timeouts, token/cost tracking per submission, model id + prompt version recorded. **Recognition prompts are strictly separated from grading prompts** — the transcription model never grades or rewrites; the grading model never invents unreadable text. Student text and test content are treated as data, never as instructions (prompt-injection defense). Cost control: reuse approved templates/rubrics, skip unchanged images, prefer deterministic grading, re-evaluate only affected answers after corrections.

## 10. Background processing design

Durable Redis-backed task queue with worker processes (not in-memory FastAPI background tasks). Jobs are idempotent and retryable with bounded attempts and recorded errors; processing survives restarts. Submission → page processing → recognition → grading are modeled as `ProcessingJob` records with explicit states (Uploaded/Queued/Processing/Completed/Failed).

## 11. Security considerations

Teacher auth (hashed passwords, secure sessions, protected routes), HTTPS, input + file validation, upload size limits, restricted file access, env-based secrets, API rate limiting, safe/structured logging, backups, data-retention/deletion controls. Student data is sensitive: send only answer crops + necessary grading context to AI, avoid sending names/identifiers where possible, and document third-party data-processing implications.

## 12. Major technical risks

1. **Handwriting transcription accuracy** on messy, crossed-out, multi-page pages — *the* central risk; validated in Phase 1 before anything is built on top.
2. **Crossed-out vs active text** disambiguation (dense scribbles must not be invented).
3. **Printed vs handwritten separation**, especially where handwriting starts mid-line after printed intro.
4. **Template alignment** under perspective/glare/shadow from phone photos.
5. **AI reliability/cost** (timeouts, malformed JSON, calibration of confidence).
6. **Prompt injection** via student-authored text.
7. **Grade integrity** — never overwrite approved grades; deterministic totals.

## 13. Implementation phases

Phase 0 Assessment ✅ → **Phase 1 Handwriting feasibility prototype** (next, gated) → 2 Foundation (scaffold/auth/docker) → 3 Students & tests → 4 Template editor → 5 Capture & submissions → 6 Document processing → 7 Handwriting integration → 8 Grading engine → 9 Teacher review → 10 Results/exports/PWA → 11 Testing & hardening.

## 14. Phase dependencies

1 is a go/no-go gate feeding 6–8. 2 underpins everything. 3→4→5 are sequential (test config before capture). 6 depends on 4+5; 7 integrates 1 into 6; 8 depends on 7; 9 depends on 8; 10 depends on 9; 11 spans all. Each major phase stops for review.

## 15. Testing strategy

- **Unit:** answer normalization, accepted alternatives, partial credit, score bounds, rubric totals, word counting, page ordering, question mapping, finalization validation.
- **Integration (AI mocked):** DB ops, storage, submission lifecycle, background jobs, AI adapters, overrides, reprocessing, exports.
- **E2E:** full login → test → template → regions → key approval → student → capture/upload → processing → extraction → grading → correction → override → approval → finalize → export.
- **Failure scenarios:** missing/duplicate/blurry pages, wrong template, unreadable/dense crossouts, missing answers, invalid/timeout AI, worker crash, network loss, invalid totals, concurrent edits, duplicate finalization, reprocessing approved submissions. **Never silently overwrite approved data.**

## 16. Acceptance criteria (per phase)

Each phase has explicit acceptance criteria from the brief (e.g. Phase 2: app runs locally + teacher login works; Phase 5: a complete paper test uploads for a specific student; Phase 9: a full submission can be reviewed, corrected, and finalized). The overall MVP "Definition of Done" is the 23-step teacher workflow in the brief, plus safe handling of processing failures and prevention of invalid/incomplete final grades.

---

## Needs validation through real handwriting samples

The following assumptions **cannot** be accepted on faith and are the explicit subject of Phase 1:
transcription fidelity (errors preserved), crossed-out exclusion, printed/handwritten separation,
multi-page merge + reading order, deterministic word count correctness, and whether useful writing
feedback can be produced. Accuracy numbers will be **measured** against `reference-transcription.md`,
never invented.
