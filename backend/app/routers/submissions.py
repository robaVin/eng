"""Submission lifecycle: upload pages -> analyze -> review -> save -> reopen."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import grading, storage
from ..ai import provider
from ..auth import AuthDep
from ..db import get_db
from ..models import Submission, Test
from ..schemas import ReviewSave, SubmissionOut, SubmissionSummary

router = APIRouter(prefix="/api/submissions", tags=["submissions"], dependencies=[AuthDep])


def _get(db: Session, submission_id: int) -> Submission:
    s = db.get(Submission, submission_id)
    if not s:
        raise HTTPException(404, "Submission not found")
    return s


@router.post("", response_model=SubmissionOut)
async def create_submission(
    student_name: str = Form(...),
    test_id: int = Form(...),
    files: list[UploadFile] = [],  # noqa: B006  (FastAPI handles this)
    db: Session = Depends(get_db),
):
    if not student_name.strip():
        raise HTTPException(400, "Student name is required.")
    test = db.get(Test, test_id)
    if not test:
        raise HTTPException(404, "Test not found.")
    if not files:
        raise HTTPException(400, "Upload at least one page image.")

    sub = Submission(student_name=student_name.strip(), test_id=test_id, status="uploaded", image_paths=[])
    db.add(sub)
    db.commit()
    db.refresh(sub)

    paths: list[str] = []
    try:
        for idx, f in enumerate(files):
            data = await f.read()
            rel = storage.validate_and_save(sub.id, idx, f.filename or f"page{idx}.jpg", data)
            paths.append(rel)
    except storage.InvalidImageError as exc:
        db.delete(sub)
        db.commit()
        raise HTTPException(400, str(exc)) from exc

    sub.image_paths = paths
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


def _load_images(sub: Submission) -> list[tuple[bytes, str]]:
    out = []
    for rel in sub.image_paths or []:
        out.append((storage.read_bytes(rel), storage.media_type_for(rel)))
    return out


def _seed_scores(evaluation: dict, rubric: list[dict] | None) -> dict[str, float]:
    """Start approved scores from AI suggestions, keyed by the rubric criterion names."""
    suggested = grading.suggested_scores_from_evaluation(evaluation)
    scores: dict[str, float] = {}
    for item in rubric or []:
        name = item["name"]
        scores[name] = round(min(float(suggested.get(name, 0)), float(item["points"])), 2)
    return scores


@router.post("/{submission_id}/analyze", response_model=SubmissionOut)
def analyze(submission_id: int, db: Session = Depends(get_db)):
    sub = _get(db, submission_id)
    test = db.get(Test, sub.test_id)
    if not test:
        raise HTTPException(404, "Test not found.")
    if not sub.image_paths:
        raise HTTPException(400, "This submission has no page images.")

    sub.status = "analyzing"
    sub.error_message = None
    db.commit()

    try:
        # Step 1: transcription (vision) — never corrects the student's writing.
        images = _load_images(sub)
        tr, tr_usage = provider.transcribe(
            images, test_title=test.title, instructions=test.instructions
        )
        transcription = tr.transcription
        word_count = grading.count_words(transcription)

        # Step 2: evaluation (separate operation) — operates on the transcription only.
        ev, ev_usage = provider.evaluate(
            test_type=test.test_type,
            title=test.title,
            instructions=test.instructions,
            criteria=test.criteria,
            max_points=test.max_points,
            expected_answer=test.expected_answer,
            rubric=test.rubric,
            word_min=test.word_min,
            word_max=test.word_max,
            transcription=transcription,
            word_count=word_count,
        )
    except provider.AIError as exc:
        sub.status = "error"
        sub.error_message = str(exc)
        db.commit()
        # 503 when unconfigured, else 502 for an upstream AI failure.
        code = 503 if isinstance(exc, provider.AINotConfiguredError) else 502
        raise HTTPException(code, str(exc)) from exc

    sub.original_transcription = transcription
    sub.corrected_transcription = transcription
    sub.word_count = word_count
    sub.transcription_meta = {
        "uncertain_passages": tr.uncertain_passages,
        "crossed_out_notes": tr.crossed_out_notes,
        "pages": tr.pages,
        "usage": {"transcription": tr_usage, "evaluation": ev_usage},
    }
    sub.evaluation = ev.model_dump()
    sub.approved_scores = _seed_scores(sub.evaluation, test.rubric)
    sub.final_score = grading.compute_total(sub.approved_scores, test.rubric, test.max_points)
    sub.status = "analyzed"
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


@router.post("/{submission_id}/reevaluate", response_model=SubmissionOut)
def reevaluate(submission_id: int, body: dict | None = None, db: Session = Depends(get_db)):
    """Re-run ONLY the evaluation against the (possibly corrected) transcription.
    No image re-upload, no re-transcription. Refreshes AI suggestions.
    """
    sub = _get(db, submission_id)
    test = db.get(Test, sub.test_id)
    if not test:
        raise HTTPException(404, "Test not found.")

    if body and isinstance(body.get("corrected_transcription"), str):
        sub.corrected_transcription = body["corrected_transcription"]
    text = sub.corrected_transcription or sub.original_transcription
    if not text:
        raise HTTPException(400, "Nothing to evaluate — run Analyze first.")

    word_count = grading.count_words(text)
    try:
        ev, ev_usage = provider.evaluate(
            test_type=test.test_type,
            title=test.title,
            instructions=test.instructions,
            criteria=test.criteria,
            max_points=test.max_points,
            expected_answer=test.expected_answer,
            rubric=test.rubric,
            word_min=test.word_min,
            word_max=test.word_max,
            transcription=text,
            word_count=word_count,
        )
    except provider.AIError as exc:
        code = 503 if isinstance(exc, provider.AINotConfiguredError) else 502
        raise HTTPException(code, str(exc)) from exc

    sub.word_count = word_count
    sub.evaluation = ev.model_dump()
    meta = dict(sub.transcription_meta or {})
    meta.setdefault("usage", {})["evaluation"] = ev_usage
    sub.transcription_meta = meta
    # Refresh suggested scores from the new evaluation (teacher can still edit before saving).
    sub.approved_scores = _seed_scores(sub.evaluation, test.rubric)
    sub.final_score = grading.compute_total(sub.approved_scores, test.rubric, test.max_points)
    if sub.status != "approved":
        sub.status = "analyzed"
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


@router.patch("/{submission_id}/review", response_model=SubmissionOut)
def save_review(submission_id: int, body: ReviewSave, db: Session = Depends(get_db)):
    sub = _get(db, submission_id)
    test = db.get(Test, sub.test_id)
    if not test:
        raise HTTPException(404, "Test not found.")

    if body.corrected_transcription is not None:
        sub.corrected_transcription = body.corrected_transcription
        sub.word_count = grading.count_words(body.corrected_transcription)
    if body.approved_scores is not None:
        sub.approved_scores = body.approved_scores
    if body.teacher_comments is not None:
        sub.teacher_comments = body.teacher_comments

    # Total is deterministic: use explicit final_score only if the teacher set one.
    if body.final_score is not None:
        sub.final_score = max(0.0, min(float(body.final_score), float(test.max_points)))
    else:
        sub.final_score = grading.compute_total(sub.approved_scores, test.rubric, test.max_points)

    sub.status = "approved"
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


@router.get("", response_model=list[SubmissionSummary])
def list_submissions(db: Session = Depends(get_db)):
    rows = db.scalars(select(Submission).order_by(Submission.created_at.desc())).all()
    out = []
    for s in rows:
        out.append(
            SubmissionSummary(
                id=s.id,
                student_name=s.student_name,
                test_id=s.test_id,
                test_title=s.test.title if s.test else None,
                status=s.status,
                final_score=s.final_score,
                created_at=s.created_at,
            )
        )
    return out


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    return SubmissionOut.model_validate(_get(db, submission_id))


@router.get("/{submission_id}/pages/{index}")
def get_page_image(submission_id: int, index: int, db: Session = Depends(get_db)):
    sub = _get(db, submission_id)
    paths = sub.image_paths or []
    if index < 0 or index >= len(paths):
        raise HTTPException(404, "Page not found")
    rel = paths[index]
    return Response(content=storage.read_bytes(rel), media_type=storage.media_type_for(rel))


@router.delete("/{submission_id}")
def delete_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = _get(db, submission_id)
    db.delete(sub)
    db.commit()
    return {"ok": True}
