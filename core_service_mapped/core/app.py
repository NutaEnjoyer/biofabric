from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.health.router import router as health_router
from core.auth.router import router as auth_router
from core.docs.router import router as docs_router
from core.docs.webhook_onlyoffice import router as oo_router
from core.workflow.router import router as wf_router
from core.notifications.router import router as notify_router
from core.jobs.router import router as jobs_router
from core.integrations.router import router as integrations_router
from core.comments.router import router as comments_router
from core.deadlines.router import router as deadlines_router
from core.audit.router import router as audit_router

app = FastAPI(title="Core API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router, prefix="/v1/core", tags=["health"])
app.include_router(auth_router, prefix="/v1/core", tags=["auth"])
app.include_router(docs_router, prefix="/v1/core", tags=["docs"])
app.include_router(oo_router, prefix="/v1/core", tags=["docs"])
app.include_router(wf_router, prefix="/v1/core", tags=["workflow"])
app.include_router(notify_router, prefix="/v1/core", tags=["notifications"])
app.include_router(jobs_router, prefix="/v1/core", tags=["jobs"])
app.include_router(integrations_router, prefix="/v1/core", tags=["integrations"])
app.include_router(comments_router, prefix="/v1/core", tags=["comments"])
app.include_router(deadlines_router, prefix="/v1/core", tags=["deadlines"])
app.include_router(audit_router, prefix="/v1/core", tags=["audit"])
