import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx
from fastapi.testclient import TestClient

from app.agent_runtime import MetaModelProvider
from app.main import app


client = TestClient(app)


def test_provider_status_is_safe_and_deterministic(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    response = client.get("/api/providers/status")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["readiness"] == "demo_no_network"
    assert body["tavily"]["readiness"] == "not_configured"
    assert "api_key" not in json.dumps(body).lower()


def test_meta_provider_uses_bearer_header_and_raw_response(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-secret")
    provider = MetaModelProvider()
    captured = {}

    def fake_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            200,
            json={"id": "resp-1", "output": [{"content": [{"type": "output_text", "text": '{"status":"completed","evidence":["finance:2026-10"]}'}]}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.agent_runtime.httpx.post", fake_post)
    result = provider.invoke(role="finance", prompt="summarize", response_schema={"type": "object"})
    assert result["status"] == "completed"
    assert captured["url"].endswith("/responses")
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert "test-secret" not in json.dumps(result)


def test_meta_provider_requires_credentials(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    provider = MetaModelProvider()
    try:
        provider.invoke(role="finance", prompt="summarize", response_schema={"type": "object"})
    except RuntimeError as exc:
        assert "MODEL_API_KEY" in str(exc)
    else:
        raise AssertionError("Missing credentials must fail closed.")


def test_final_frontend_sections_and_provider_status_are_wired():
    html = (Path(__file__).parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    script = (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
    for section in ("overview", "intelligence", "investigations", "scenarios", "audit", "system"):
        assert f'id="{section}"' in html
    assert "/api/providers/status" in script
    assert "/api/investigate" in script
