from fastapi import APIRouter, Depends
from sqlalchemy import text
from core.db import get_db

router = APIRouter()

@router.get("/healthz")
def healthz():
    """Базовая проверка жизни сервиса."""
    return {"status": "ok"}

@router.get("/readyz")
def readyz(db=Depends(get_db)):
    """Проверка готовности (включая БД)."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return {"status": "not_ready", "db": "error", "detail": str(e)}
