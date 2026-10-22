"""Pydantic schemas: API request/response models AND validated AI outputs."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TestType = Literal["grammar", "vocabulary", "reading", "writing"]


# ---------- Rubric ----------
class RubricItem(BaseModel):
    name: str
    points: float = Field(ge=0)


# ---------- Test config ----------
class TestCreate(BaseModel):
    title: str
    test_type: TestType
    instructions: str = ""
    max_points: float = Field(gt=0, default=10)
    criteria: str = ""
    expected_answer: str | None = None
    rubric: list[RubricItem] | None = None
    word_min: int | None = None
    word_max: int | None = None

    @field_validator("rubric")
    @classmethod
    def _non_empty_names(cls, v: list[RubricItem] | None) -> list[RubricItem] | None:
        if v:
            for item in v:
                if not item.name.strip():
                    raise ValueError("Rubric criteria must have names")
        return v


class TestOut(BaseModel):
    id: int
    title: str
    test_type: str
    instructions: str
    max_points: float
    criteria: str
    expected_answer: str | None
    rubric: list[RubricItem] | None
    word_min: int | None
    word_max: int | None
    has_test_image: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Validated AI output: transcription ----------
class TranscriptionResult(BaseModel):
    transcription: str = ""
    uncertain_passages: list[str] = []
    crossed_out_notes: list[str] = []
    pages: list[dict] = []


# ---------- Validated AI output: evaluation ----------
class WritingIssue(BaseModel):
    # grammar | spelling | punctuation (free-form tolerated)
    type: str
    original: str = ""
    correction: str = ""
    explanation: str = ""


class RubricScoreSuggestion(BaseModel):
    criterion: str
    max_points: float = 0
    suggested_points: float = 0
    explanation: str = ""


class EvaluationResult(BaseModel):
    issues: list[WritingIssue] = []
    rubric_scores: list[RubricScoreSuggestion] = []
    overall_feedback: str = ""
    notes: list[str] = []


# ---------- Submission API ----------
class SubmissionOut(BaseModel):
    id: int
    student_name: str
    test_id: int
    status: str
    error_message: str | None
    image_paths: list
    original_transcription: str | None
    corrected_transcription: str | None
    word_count: int | None
    transcription_meta: dict | None
    evaluation: dict | None
    approved_scores: dict | None
    final_score: float | None
    teacher_comments: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubmissionSummary(BaseModel):
    id: int
    student_name: str
    test_id: int
    test_title: str | None = None
    status: str
    final_score: float | None
    created_at: datetime


class TranscriptionUpdate(BaseModel):
    corrected_transcription: str


class ReviewSave(BaseModel):
    corrected_transcription: str | None = None
    approved_scores: dict[str, float] | None = None
    final_score: float | None = None
    teacher_comments: str | None = None
