from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db
import json, uuid

router = APIRouter()

class JobIn(BaseModel):
    type: str
    run_at: str | None = None
    payload: dict | None = None
    idempotency_key: str | None = None

@router.post("/jobs")
def create_job(body: JobIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO jobs(id, type, payload_json, run_at, status, attempts, idempotency_key, created_at) VALUES (:id,:t,:p, COALESCE(:r, NOW()), 'pending', 0, :k, NOW())"),
               {"id": str(uuid.uuid4()), "t": body.type, "p": json.dumps(body.payload or {}), "r": body.run_at, "k": body.idempotency_key})
    db.commit()
    return {"ok": True}

@router.get("/jobs")
def list_jobs(limit: int = 50, db = Depends(get_db)):
    rows = db.execute(text("SELECT id, type, status, attempts, run_at FROM jobs ORDER BY run_at ASC LIMIT :l"), {"l": limit}).mappings().all()
    return {"items": [dict(r) for r in rows]}
