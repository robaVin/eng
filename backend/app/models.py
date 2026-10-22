"""SQLAlchemy ORM models for the prototype.

Kept intentionally small: a Test holds configuration + rubric, a Submission holds
one student's uploaded pages plus the transcription, evaluation, and approved grade.
JSON columns are used for the flexible, nested parts (rubric, evaluation, scores).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    # one of: grammar | vocabulary | reading | writing
    test_type: Mapped[str] = mapped_column(String(40))
    instructions: Mapped[str] = mapped_column(Text, default="")
    max_points: Mapped[float] = mapped_column(Float, default=10)
    criteria: Mapped[str] = mapped_column(Text, default="")
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # rubric: list[{"name": str, "points": float}]
    rubric: Mapped[list | None] = mapped_column(JSON, nullable=True)
    original_test_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="test", cascade="all, delete-orphan"
    )


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_name: Mapped[str] = mapped_column(String(200))
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"))
    # uploaded | analyzing | analyzed | approved | error
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ordered list of stored image file paths (relative to uploads dir)
    image_paths: Mapped[list] = mapped_column(JSON, default=list)

    original_transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI structured outputs
    transcription_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # teacher-approved per-criterion scores: {criterion_name: points}
    approved_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    test: Mapped[Test] = relationship(back_populates="submissions")
