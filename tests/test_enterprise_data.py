import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_enterprise_catalog_has_all_domains_and_twelve_months():
    response = client.get("/api/sources")
    assert response.status_code == 200
    body = response.json()
    assert body["quality"]["valid"] is True
    assert body["quality"]["record_count"] >= 120
    assert {item["domain"] for item in body["sources"]} == {
        "finance", "sales", "projects", "hiring", "workforce", "learning",
        "ai_transformation", "cloud", "facilities", "external_intelligence",
    }


def test_domain_and_business_unit_queries_are_local_and_filtered():
    records = client.get("/api/data/domain/finance").json()["records"]
    assert len(records) == 12
    assert all(record["currency"] == "USD" for record in records)
    unit = client.get("/api/business-units/bu:cloud-infrastructure").json()
    assert unit["domains"]["cloud"]
    assert all(item["business_unit_id"] == "bu:cloud-infrastructure" for item in unit["domains"]["cloud"])


def test_dataset_validation_reports_duplicates_and_ingestion_persists_snapshot():
    payload = {"finance": [{"record_id": "duplicate", "source_id": "x", "ingestion_timestamp": "2026-10-31"}]}
    first = client.post("/api/data/validate", json=payload)
    assert first.status_code == 200
    assert first.json()["valid"] is True
    duplicated = {"finance": payload["finance"] * 2}
    result = client.post("/api/data/validate", json=duplicated).json()
    assert result["valid"] is False
    assert any(item["duplicate"] for item in result["records"])

    ingest = client.post("/api/data/ingest", json={"data": client.get("/api/data/domain/finance").json()})
    assert ingest.status_code == 200
    assert ingest.json()["status"] == "accepted"
    assert any(item["snapshot_id"] == ingest.json()["snapshot_id"] for item in client.get("/api/data/snapshots").json())
