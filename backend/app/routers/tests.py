"""Test (assignment) configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import grading, storage
from ..auth import AuthDep
from ..db import get_db
from ..models import Test
from ..schemas import RubricItem, TestCreate, TestOut

router = APIRouter(prefix="/api/tests", tags=["tests"], dependencies=[AuthDep])


def _to_out(t: Test) -> TestOut:
    return TestOut(
        id=t.id,
        title=t.title,
        test_type=t.test_type,
        instructions=t.instructions,
        max_points=t.max_points,
        criteria=t.criteria,
        expected_answer=t.expected_answer,
        rubric=[RubricItem(**r) for r in (t.rubric or [])],
        word_min=t.word_min,
        word_max=t.word_max,
        has_test_image=bool(t.original_test_image),
        created_at=t.created_at,
    )


@router.get("/defaults/writing-rubric")
def writing_rubric_default(max_points: float = 10):
    if max_points <= 0:
        raise HTTPException(400, "max_points must be positive")
    return [r.model_dump() for r in grading.default_writing_rubric(max_points)]


@router.post("", response_model=TestOut)
def create_test(body: TestCreate, db: Session = Depends(get_db)):
    rubric = body.rubric
    if body.test_type == "writing":
        if not rubric:
            rubric = grading.default_writing_rubric(body.max_points)
        elif not grading.rubric_matches_max(rubric, body.max_points):
            raise HTTPException(
                400,
                f"Rubric points total {grading.rubric_total(rubric)} must equal "
                f"max points {body.max_points}.",
            )
    else:
        # short-answer style: a single criterion worth all the points
        if not rubric:
            rubric = [RubricItem(name="Overall", points=body.max_points)]
        elif not grading.rubric_matches_max(rubric, body.max_points):
            raise HTTPException(
                400,
                f"Rubric points total {grading.rubric_total(rubric)} must equal "
                f"max points {body.max_points}.",
            )

    t = Test(
        title=body.title,
        test_type=body.test_type,
        instructions=body.instructions,
        max_points=body.max_points,
        criteria=body.criteria,
        expected_answer=body.expected_answer,
        rubric=[r.model_dump() for r in rubric],
        word_min=body.word_min,
        word_max=body.word_max,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.get("", response_model=list[TestOut])
def list_tests(db: Session = Depends(get_db)):
    rows = db.scalars(select(Test).order_by(Test.created_at.desc())).all()
    return [_to_out(t) for t in rows]


@router.get("/{test_id}", response_model=TestOut)
def get_test(test_id: int, db: Session = Depends(get_db)):
    t = db.get(Test, test_id)
    if not t:
        raise HTTPException(404, "Test not found")
    return _to_out(t)


@router.post("/{test_id}/image", response_model=TestOut)
async def upload_test_image(test_id: int, file: UploadFile, db: Session = Depends(get_db)):
    t = db.get(Test, test_id)
    if not t:
        raise HTTPException(404, "Test not found")
    data = await file.read()
    try:
        rel = storage.validate_and_save(0, 0, file.filename or "test.jpg", data)
    except storage.InvalidImageError as exc:
        raise HTTPException(400, str(exc)) from exc
    t.original_test_image = rel
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.get("/{test_id}/image")
def get_test_image(test_id: int, db: Session = Depends(get_db)):
    t = db.get(Test, test_id)
    if not t or not t.original_test_image:
        raise HTTPException(404, "No test image")
    return Response(
        content=storage.read_bytes(t.original_test_image),
        media_type=storage.media_type_for(t.original_test_image),
    )


@router.delete("/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db)):
    t = db.get(Test, test_id)
    if not t:
        raise HTTPException(404, "Test not found")
    db.delete(t)
    db.commit()
    return {"ok": True}
