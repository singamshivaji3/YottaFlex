"""
Integration and functional tests for the FastAPI Web Application & REST API endpoints.
"""

import pytest
from starlette.testclient import TestClient

from src.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_healthcheck(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database_counts" in data
    assert "learners" in data["database_counts"]


def test_overview_endpoint(client):
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "active_learners" in data
    assert "recommendation_coverage" in data


def test_list_learners(client):
    response = client.get("/api/learners?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert len(data["items"]) <= 10
    assert "learner_id" in data["items"][0]


def test_learner_profile(client):
    response = client.get("/api/learners/LRN-000001")
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["learner_id"] == "LRN-000001"
    assert "recent_attempts" in data
    assert "mastery_summary" in data


def test_learner_mastery_endpoint(client):
    response = client.get("/api/learners/LRN-000001/mastery")
    assert response.status_code == 200
    data = response.json()
    assert data["learner_id"] == "LRN-000001"
    assert "skills" in data
    assert len(data["skills"]) > 0
    assert "mastery_score" in data["skills"][0]


def test_learner_recommendations_endpoint(client):
    response = client.get("/api/learners/LRN-000001/recommendations?top_k=3")
    assert response.status_code == 200
    data = response.json()
    assert data["learner_id"] == "LRN-000001"
    assert "recommendations" in data
    assert "blocked_activities" in data
    if len(data["recommendations"]) > 0:
        rec = data["recommendations"][0]
        assert "content_id" in rec
        assert "score" in rec
        assert "reason_code" in rec
        assert "reason_description" in rec


def test_submit_attempt_endpoint(client):
    payload = {
        "learner_id": "LRN-000001",
        "content_id": "CNT-000001",
        "score": 0.95,
        "status": "completed",
        "duration_minutes": 20,
    }
    response = client.post("/api/attempts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "attempt_id" in data
    assert data["learner_id"] == "LRN-000001"
    assert "assessments_created" in data


def test_skills_prerequisites_graph(client):
    response = client.get("/api/skills/prerequisites-graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0
    assert "is_acyclic" in data
    assert data["is_acyclic"] is True
    assert data["cycle_count"] == 0


def test_content_items_endpoint(client):
    response = client.get("/api/content-items?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= 10
    assert len(data["items"]) > 0
    item = data["items"][0]
    assert "content_id" in item
    assert "title" in item
    assert "content_type" in item


def test_tables_explorer_valid_and_invalid(client):
    # Valid table
    response = client.get("/api/tables/courses?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["table"] == "courses"
    assert "columns" in data
    assert "course_id" in data["columns"]
    assert "rows" in data
    assert len(data["rows"]) > 0

    # Whitelist rejection: SQL injection / invalid table
    bad_resp = client.get("/api/tables/users_passwords;DROP TABLE--")
    assert bad_resp.status_code == 400


def test_validation_endpoint(client):
    response = client.get("/api/validation")
    assert response.status_code == 200
    data = response.json()
    assert "total_checks" in data
    assert "is_valid" in data
    assert data["is_valid"] is True


def test_anomalies_endpoint(client):
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert data["total_fixtures"] == 5
    assert data["detected_count"] == 5


def test_all_five_anomalies_detected_individually(client):
    for case_id in ["ANOM-001", "ANOM-002", "ANOM-003", "ANOM-004", "ANOM-005"]:
        response = client.post(f"/api/anomalies/detect/{case_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == case_id
        assert data["detected"] is True
        assert data["status"] == "DETECTED_AND_ISOLATED"
        assert len(data["message"]) > 0


def test_web_ui_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "YottaFlex AI" in response.text
    assert "Learning Recommendation Engine" in response.text
