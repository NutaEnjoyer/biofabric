"""
OKS Service — FastAPI Application
Модуль ОКС: объекты капитального строительства, этапы, документы, аналитика.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from oks.api.router_objects import router as objects_router
from oks.api.router_stages import router as stages_router
from oks.api.router_documents import router as documents_router
from oks.api.router_comments import router as comments_router
from oks.api.router_analytics import router as analytics_router
from oks.api.deps import get_db

app = FastAPI(
    title="OKS Service (Капитальное строительство)",
    description="API модуля ОКС ERP-Биофабрика: объекты, этапы, документы, аналитика.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(objects_router,   prefix="/v1/oks")
app.include_router(stages_router,    prefix="/v1/oks")
app.include_router(documents_router, prefix="/v1/oks")
app.include_router(comments_router,  prefix="/v1/oks")
app.include_router(analytics_router, prefix="/v1/oks")


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz(db=Depends(get_db)):
    try:
        cur = db.cursor()
        cur.execute("SELECT 1")
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return {"status": "not_ready", "db": "error", "detail": str(e)}
