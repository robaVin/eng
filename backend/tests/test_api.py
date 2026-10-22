"""End-to-end API workflow tests with the AI layer mocked."""


def _create_writing_test(client):
    r = client.post(
        "/api/tests",
        json={
            "title": "The Mysterious Letter",
            "test_type": "writing",
            "instructions": "Continue the story in 150-180 words.",
            "max_points": 10,
            "criteria": "Creative, logical, correct grammar and punctuation.",
            "word_min": 150,
            "word_max": 180,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_requires_auth():
    from fastapi.testclient import TestClient

    from app.main import app

    anon = TestClient(app)
    assert anon.get("/api/tests").status_code == 401


def test_writing_test_gets_default_rubric(client):
    t = _create_writing_test(client)
    assert len(t["rubric"]) == 5
    assert abs(sum(r["points"] for r in t["rubric"]) - 10) < 0.01


def test_rubric_mismatch_rejected(client):
    r = client.post(
        "/api/tests",
        json={
            "title": "Bad", "test_type": "writing", "max_points": 10,
            "rubric": [{"name": "Only", "points": 5}],
        },
    )
    assert r.status_code == 400


def test_full_workflow(client, mock_ai, png):
    t = _create_writing_test(client)

    # upload two pages as one submission
    r = client.post(
        "/api/submissions",
        data={"student_name": "Emma", "test_id": t["id"]},
        files=[
            ("files", ("page1.png", png, "image/png")),
            ("files", ("page2.png", png, "image/png")),
        ],
    )
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["status"] == "uploaded"
    assert len(sub["image_paths"]) == 2

    # analyze (mocked AI)
    r = client.post(f"/api/submissions/{sub['id']}/analyze")
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["status"] == "analyzed"
    assert "third ring" in sub["original_transcription"]
    assert sub["corrected_transcription"] == sub["original_transcription"]
    assert sub["word_count"] > 0
    assert sub["evaluation"]["issues"][0]["original"] == "wierd"
    assert sub["transcription_meta"]["uncertain_passages"] == ["breathiy"]
    # scores seeded from suggestions; total within max
    assert sub["final_score"] <= t["max_points"]

    # page image is served (auth-protected)
    assert client.get(f"/api/submissions/{sub['id']}/pages/0").status_code == 200
    assert client.get(f"/api/submissions/{sub['id']}/pages/9").status_code == 404

    # edit transcription + reevaluate (no re-upload)
    r = client.post(
        f"/api/submissions/{sub['id']}/reevaluate",
        json={"corrected_transcription": "She answered the phone after the third ring. It was weird now."},
    )
    assert r.status_code == 200, r.text
    sub = r.json()
    assert "weird now" in sub["corrected_transcription"]

    # save review with teacher overrides
    r = client.patch(
        f"/api/submissions/{sub['id']}/review",
        json={
            "approved_scores": {rr["name"]: rr["points"] for rr in t["rubric"]},
            "teacher_comments": "Well done.",
        },
    )
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["status"] == "approved"
    assert sub["final_score"] == t["max_points"]  # all criteria full marks
    assert sub["teacher_comments"] == "Well done."

    # reopen later
    r = client.get(f"/api/submissions/{sub['id']}")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # appears in the results list
    r = client.get("/api/submissions")
    assert r.status_code == 200
    assert any(s["id"] == sub["id"] and s["student_name"] == "Emma" for s in r.json())


def test_invalid_image_rejected(client):
    t = _create_writing_test(client)
    r = client.post(
        "/api/submissions",
        data={"student_name": "X", "test_id": t["id"]},
        files=[("files", ("notimage.txt", b"hello", "text/plain"))],
    )
    assert r.status_code == 400
