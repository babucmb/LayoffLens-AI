import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_linked_review_captures_real_evidence_and_lifecycle():
    investigation = client.post("/api/investigate", json={"budget": 6}).json()
    response = client.post(
        "/api/reviews",
        json={
            "investigation_id": investigation["run_id"],
            "recommendation": "needs_evidence",
            "rationale": "Review the validated aggregate evidence before deciding.",
        },
    )
    assert response.status_code == 200
    review = response.json()
    assert review["investigation_id"] == investigation["run_id"]
    assert review["evidence_snapshot"]["evidence"]
    assert review["actor"] == "demo"
    assert all(item["evidence_id"] in investigation["brief"]["evidence"] for item in review["evidence_snapshot"]["evidence"])

    comment = client.post(f"/api/reviews/{review['id']}/comments", json={"comment": "Please document the source timing."})
    assert comment.status_code == 200
    transition = client.post(
        f"/api/reviews/{review['id']}/transition",
        json={"status": "in_review", "rationale": "Evidence request is being assessed."},
    )
    assert transition.status_code == 200
    assert transition.json()["lifecycle_status"] == "in_review"
    assert any(item["activity_type"] == "comment" for item in transition.json()["activity"])


def test_fabricated_review_evidence_is_rejected():
    investigation = client.post("/api/investigate", json={"budget": 6}).json()
    review = client.post(
        "/api/reviews",
        json={
            "investigation_id": investigation["run_id"],
            "recommendation": "accepted",
            "rationale": "The available evidence supports this review decision.",
        },
    ).json()
    response = client.post(
        f"/api/reviews/{review['id']}/evidence",
        json={"evidence": ["fabricated:record"]},
    )
    assert response.status_code == 422


def test_audit_route_is_role_restricted_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("WRI_AUTH_ENABLED", "true")
    reviewer = client.post("/api/auth/login", json={"username": "reviewer", "password": "reviewer-demo"}).json()["token"]
    operator = client.post("/api/auth/login", json={"username": "operator", "password": "operator-demo"}).json()["token"]
    reviewer_headers = {"Authorization": f"Bearer {reviewer}", "X-WRI-Tenant": "demo-tenant"}
    operator_headers = {"Authorization": f"Bearer {operator}", "X-WRI-Tenant": "demo-tenant"}
    assert client.get("/api/audit", headers=reviewer_headers).status_code == 403
    assert client.get("/api/audit", headers=operator_headers).status_code == 200
    monkeypatch.setenv("WRI_AUTH_ENABLED", "false")
