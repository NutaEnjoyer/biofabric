from fastapi import FastAPI
from .api.router_ops import router as ops_router
from .api.router_import import router as import_router
from .api.router_reports import router as reports_router
from .api.router_refs import router as refs_router
from .api.deps import lifespan

app = FastAPI(title="Quarantine Animals Module", version="0.1.0", lifespan=lifespan)

app.include_router(ops_router,     prefix="/v1/quarantine", tags=["operations"])
app.include_router(import_router,  prefix="/v1/quarantine", tags=["import"])
app.include_router(reports_router, prefix="/v1/quarantine", tags=["reports"])
app.include_router(refs_router,    prefix="/v1/quarantine", tags=["references"])

@app.get("/health")
def health():
    return {"status": "ok"}
