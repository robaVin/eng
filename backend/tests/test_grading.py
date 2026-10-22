"""Unit tests for deterministic grading logic."""
from app import grading
from app.schemas import RubricItem


def test_count_words_basic():
    assert grading.count_words("She went to school.") == 4
    assert grading.count_words("") == 0
    assert grading.count_words(None) == 0


def test_count_words_contractions_and_hyphens():
    # contractions and hyphenated words count as one token each
    assert grading.count_words("don't over-think it") == 3


def test_default_writing_rubric_totals_match():
    r = grading.default_writing_rubric(10)
    assert len(r) == 5
    assert abs(grading.rubric_total(r) - 10) < 0.01


def test_default_writing_rubric_odd_total():
    r = grading.default_writing_rubric(7)
    assert abs(grading.rubric_total(r) - 7) < 0.01


def test_rubric_matches_max():
    r = [RubricItem(name="A", points=4), RubricItem(name="B", points=6)]
    assert grading.rubric_matches_max(r, 10)
    assert not grading.rubric_matches_max(r, 11)


def test_compute_total_clamps_per_criterion_and_overall():
    rubric = [{"name": "A", "points": 4}, {"name": "B", "points": 6}]
    # A exceeds its cap (clamped to 4); total clamped to max 10
    total = grading.compute_total({"A": 99, "B": 6}, rubric, 10)
    assert total == 10
    # negative scores floored at 0
    assert grading.compute_total({"A": -5, "B": 3}, rubric, 10) == 3
    # no scores -> 0
    assert grading.compute_total({}, rubric, 10) == 0


def test_suggested_scores_from_evaluation():
    ev = {"rubric_scores": [{"criterion": "A", "suggested_points": 3.5}]}
    assert grading.suggested_scores_from_evaluation(ev) == {"A": 3.5}
