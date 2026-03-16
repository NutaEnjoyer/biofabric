"""API для задач генерации контент-плана (mk_plan_jobs).

ТЗ п.1, п.5: постановка задачи → ИИ генерирует черновики.
Workflow: создать задачу → запустить → получить результат в /posts (корзина идей).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import metadata
from ..api.deps import get_db, get_user, get_core, can
from ..schemas.dto_plan_jobs import PlanJobCreate, PlanJobRead
from ..schemas.dto_common import ResponseOk
from ..repositories.plan_jobs_repo import PlanJobsRepo
from ..services.ai_plan import AIPlanService

router = APIRouter()


@router.post("/plan-jobs", response_model=ResponseOk)
async def create_plan_job(
    payload: PlanJobCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_user),
    core=Depends(get_core),
):
    """Создать задачу на ИИ-генерацию контент-плана.

    Что происходит:
    1. Запись задачи в mk_plan_jobs (status=pending).
    2. Немедленный запуск генерации (status→running→done).
    3. Черновики постов без дат появляются в корзине идей (GET /ideas).

    ТЗ п.1: «Постановка задач на генерацию контент-планов по направлениям».
    ТЗ п.5: «Уточнение целевой аудитории и ключевых сообщений»."""
    if not can(user, "create_post", "post"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    repo = PlanJobsRepo(metadata)
    job_data = payload.model_dump()
    job_data["created_by"] = user.user_id
    job_id = await repo.create(db, job_data)

    # Запускаем генерацию синхронно (MVP; в prod — фоновая задача)
    await repo.set_status(db, job_id, "running")
    try:
        # Формируем промт из параметров задачи
        prompt_parts = []
        if payload.audience:
            prompt_parts.append(f"Аудитория: {payload.audience}")
        if payload.goals:
            prompt_parts.append(f"Цели: {payload.goals}")
        if payload.tone:
            prompt_parts.append(f"Стиль: {payload.tone}")
        prompt_parts.append(
            f"Период: {payload.period_start} — {payload.period_end}"
        )
        prompt = ". ".join(prompt_parts)

        direction_id = payload.direction_id
        svc = AIPlanService(metadata)
        post_ids = await svc.generate_from_prompt(
            db,
            prompt=prompt,
            channels=None,
            formats=None,
        )
        await repo.set_status(db, job_id, "done")
    except Exception as exc:
        await repo.set_status(db, job_id, "failed")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {exc}") from exc

    return ResponseOk(data={"job_id": job_id, "created_post_ids": post_ids})


@router.get("/plan-jobs", response_model=ResponseOk)
async def list_plan_jobs(db: AsyncSession = Depends(get_db)):
    """Список всех задач генерации контент-плана."""
    repo = PlanJobsRepo(metadata)
    rows = await repo.list(db)
    return ResponseOk(data=rows)


@router.get("/plan-jobs/{job_id}", response_model=ResponseOk)
async def get_plan_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Карточка задачи генерации (статус, параметры)."""
    repo = PlanJobsRepo(metadata)
    row = await repo.get(db, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return ResponseOk(data=row)
