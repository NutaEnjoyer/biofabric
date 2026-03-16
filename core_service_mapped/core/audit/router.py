from fastapi import APIRouter, Depends
from sqlalchemy import text
from core.db import get_db

router = APIRouter()

@router.get('/audit')
def list_audit(limit: int = 50, db = Depends(get_db)):
    rows = db.execute(text('SELECT id, actor_user_id, actor_system, action, resource, resource_id, created_at FROM audit_log ORDER BY created_at DESC LIMIT :l'), {'l': limit}).mappings().all()
    return {'items':[dict(r) for r in rows]}
