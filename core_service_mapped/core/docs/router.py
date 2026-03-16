from fastapi import APIRouter, Depends
from sqlalchemy import text
from core.db import get_db

router = APIRouter()

@router.get("/docs/{doc_id}/versions")
def list_versions(doc_id: str, db = Depends(get_db)):
    rows = db.execute(text("SELECT id, version_no, file_path, created_at FROM document_versions WHERE document_id=:d ORDER BY version_no ASC"),
                      {"d": doc_id}).mappings().all()
    return {"items": [dict(r) for r in rows]}

@router.get("/entity/{entity_type}/{entity_id}/docs")
def entity_docs(entity_type: str, entity_id: str, db = Depends(get_db)):
    rows = db.execute(text("SELECT document_id, purpose, created_at FROM document_bindings WHERE entity_type=:t AND entity_id=:i ORDER BY created_at DESC"),
                      {"t": entity_type, "i": entity_id}).mappings().all()
    return {"items": [dict(r) for r in rows]}
