
import asyncio
import httpx
import pytest
from fastapi import status
from app.main import app

@pytest.mark.asyncio
async def test_basic_flow():
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        # health
        r = await ac.get("/health")
        assert r.status_code == 200

        # create request
        payload = {
            "subject": "Закупка серверов",
            "items": [{"nomenclature": "Сервер 2U", "quantity": 2, "tech_spec": "CPU 32 core", "due_days": 14}]
        }
        r = await ac.post("/requests", json=payload)
        assert r.status_code == 200
        req = r.json()
        req_id = req["id"]

        # add quote
        r = await ac.post("/suppliers/quotes", json={"request_id": req_id, "supplier_name": "ООО Поставщик", "price": 100000.0})
        assert r.status_code == 200

        # approve by director (routes status to in_progress)
        r = await ac.post("/approvals", json={"request_id": req_id, "user_id": 2, "decision": "Утвердить"})
        assert r.status_code == 200

        # emulate 1C webhook of stock received
        r = await ac.post(f"/integrations/1c/webhook/stock-received/{req_id}")
        assert r.status_code == 200

        # check final status
        r = await ac.get(f"/requests/{req_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "Исполнена"
