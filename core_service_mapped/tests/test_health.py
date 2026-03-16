from fastapi.testclient import TestClient
from core.app import app

def test_health():
    c = TestClient(app)
    r = c.get('/v1/core/health')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'
