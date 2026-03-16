from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db

router = APIRouter()

class DeadlineIn(BaseModel):
    entity_type: str
    entity_id: str
    due_at: str
    kind: str
    title: str
    description: str | None = None
    responsible_user_id: int | None = None

@router.post("/deadlines")
def create_deadline(body: DeadlineIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO calendar_deadlines(entity_type, entity_id, due_at, kind, title, description, responsible_user_id, status, created_at) VALUES (:t,:i,:d,:k,:ti,:ds,:u,'pending',NOW())"),
               {"t": body.entity_type, "i": body.entity_id, "d": body.due_at, "k": body.kind, "ti": body.title, "ds": body.description, "u": body.responsible_user_id})
    db.commit()
    return {"ok": True}

@router.get("/deadlines")
def list_deadlines(limit: int = 50, db = Depends(get_db)):
    rows = db.execute(text("SELECT id, entity_type, entity_id, due_at, kind, title, status FROM calendar_deadlines ORDER BY due_at ASC LIMIT :l"), {"l": limit}).mappings().all()
    return {"items": [dict(r) for r in rows]}
