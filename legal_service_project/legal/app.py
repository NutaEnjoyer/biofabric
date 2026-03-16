"""
Legal Service — FastAPI Application
Модуль юристов: договоры, согласования, гарантии, интеграции.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from legal.api.router_requests import router as legal_router
from legal.api.router_core import router as core_router
from legal.api.deps import get_db

app = FastAPI(
    title="Legal Service (Юристы)",
    description="API модуля юристов ERP-Биофабрика: договоры, workflow, KPI, интеграции.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(legal_router, prefix="/v1/legal")
app.include_router(core_router, prefix="/v1/core")


@app.get("/healthz", tags=["health"])
def healthz():
    """Проверка жизни сервиса."""
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz(db=Depends(get_db)):
    """Проверка готовности (включая БД)."""
    try:
        cur = db.cursor()
        cur.execute("SELECT 1")
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return {"status": "not_ready", "db": "error", "detail": str(e)}
