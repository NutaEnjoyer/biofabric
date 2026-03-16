"""FastAPI приложение модуля Маркетинг.

Что делает:
- Регистрирует роутеры предметной области.
- Отвечает за точку входа сервиса `/v1/marketing`.
- Никакой бизнес-логики здесь нет — только композиция.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api import router_posts, router_sources, router_ai, router_calendar, router_analytics, router_plan_jobs
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Marketing Service", version="0.1.0", lifespan=lifespan)

app.include_router(router_posts.router,       prefix="/v1/marketing", tags=["posts"])
app.include_router(router_sources.router,     prefix="/v1/marketing", tags=["sources"])
app.include_router(router_ai.router,          prefix="/v1/marketing", tags=["ai"])
app.include_router(router_calendar.router,    prefix="/v1/marketing", tags=["calendar"])
app.include_router(router_analytics.router,   prefix="/v1/marketing", tags=["analytics"])
app.include_router(router_plan_jobs.router,   prefix="/v1/marketing", tags=["plan-jobs"])
