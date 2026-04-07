"""
Integration tests for all three OpenEnv API routes.
Uses the `client` fixture from conftest.py so the FastAPI lifespan runs
and app.state.env is initialised before any request is made.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_state_before_reset():
    # Isolated fresh client — own lifespan, guaranteed no prior reset
    with TestClient(app) as fresh:
        r = fresh.get("/state")
    assert r.status_code == 200
    data = r.json()
    assert data["initialized"] is False
    assert data["current_task_id"] is None


def test_reset_easy(client):
    r = client.post("/reset", json={"task_difficulty": "easy"})
    assert r.status_code == 200
    data = r.json()
    assert data["difficulty"] == "easy"
    assert "code_snippet" in data
    assert "instructions" in data
    assert "ground_truth" not in data  # Must never be exposed


def test_reset_medium(client):
    r = client.post("/reset", json={"task_difficulty": "medium"})
    assert r.status_code == 200
    assert r.json()["difficulty"] == "medium"


def test_reset_hard(client):
    r = client.post("/reset", json={"task_difficulty": "hard"})
    assert r.status_code == 200
    assert r.json()["difficulty"] == "hard"


def test_reset_no_body(client):
    r = client.post("/reset")
    assert r.status_code == 200


def test_reset_invalid_difficulty(client):
    r = client.post("/reset", json={"task_difficulty": "impossible"})
    assert r.status_code == 404


def test_step_without_reset():
    # Isolated fresh client — own lifespan, no prior reset
    with TestClient(app) as fresh:
        r = fresh.post("/step", json={})
    assert r.status_code == 400


def test_step_after_reset_easy(client):
    client.post("/reset", json={"task_difficulty": "easy"})
    r = client.post("/step", json={"flagged_lines": [2], "findings": [], "review_text": ""})
    assert r.status_code == 200
    data = r.json()
    assert "reward" in data
    assert 0.0 <= data["reward"] <= 1.0
    assert data["done"] is True
    assert "ground_truth" not in data
    assert "ground_truth" not in data.get("observation", {})


def test_step_empty_action(client):
    client.post("/reset", json={"task_difficulty": "easy"})
    r = client.post("/step", json={})
    assert r.status_code == 200
    assert r.json()["reward"] == 0.0


def test_state_after_reset(client):
    client.post("/reset", json={"task_difficulty": "medium"})
    r = client.get("/state")
    assert r.status_code == 200
    data = r.json()
    assert data["initialized"] is True
    assert data["difficulty"] == "medium"


def test_state_after_step(client):
    client.post("/reset", json={"task_difficulty": "hard"})
    client.post("/step", json={})
    r = client.get("/state")
    assert r.status_code == 200
    data = r.json()
    assert data["step_count"] == 1
    assert data["last_reward"] is not None
