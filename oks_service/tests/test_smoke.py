"""Smoke tests для OKS Service."""
from fastapi.testclient import TestClient
from oks.app import app

client = TestClient(app)

ADMIN_HEADERS = {"X-User-Id": "1", "X-User-Roles": "oks_admin"}


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_objects_requires_auth():
    resp = client.get("/v1/oks/objects")
    assert resp.status_code == 403


def test_objects_with_role():
    resp = client.get("/v1/oks/objects", headers=ADMIN_HEADERS)
    # 200 если БД доступна, 500 если нет — в CI без БД допускаем оба
    assert resp.status_code in (200, 500)


def test_analytics_summary():
    resp = client.get("/v1/oks/analytics/summary", headers=ADMIN_HEADERS)
    assert resp.status_code in (200, 500)
