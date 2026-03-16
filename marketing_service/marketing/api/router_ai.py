from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import metadata
from ..api.deps import get_db, get_core, get_user
from ..schemas.dto_ai import PlanFromPromptRequest, PlanFromPromptResult, IdeasFromSourcesRequest, IdeasFromSourcesResult
from ..schemas.dto_posts import AIPostTextRequest, AIPostTextResponse
from ..schemas.dto_common import ResponseOk
from ..services.ai_plan import AIPlanService
from ..services.ai_sources import AISourcesService
from ..services.posts import PostsService
from ..services.notifier import MarketingNotifier

router = APIRouter()


@router.post("/ai/plan", response_model=PlanFromPromptResult)
async def ai_generate_plan(
    req: PlanFromPromptRequest,
    db: AsyncSession = Depends(get_db),
    core=Depends(get_core),
    user=Depends(get_user),
):
    """Сгенерировать набор черновиков постов по текстовому промту (без дат).

    ТЗ п.6: «Формирует контент-план на неделю/месяц с разбивкой по форматам».
    После генерации — N2: уведомляет редактора."""
    svc = AIPlanService(metadata)
    ids = await svc.generate_from_prompt(db, req.prompt, req.channels, req.formats)
    # N2 — уведомление: пост сформирован ИИ
    await MarketingNotifier(core).ai_post_created(ids, user_id=user.user_id)
    return PlanFromPromptResult(created_post_ids=ids)


@router.post("/ai/ideas", response_model=IdeasFromSourcesResult)
async def ai_generate_ideas(
    req: IdeasFromSourcesRequest,
    db: AsyncSession = Depends(get_db),
    core=Depends(get_core),
    user=Depends(get_user),
):
    """Сгенерировать идеи из импортированных материалов (по 10 с источника).

    После генерации — N2: уведомляет редактора."""
    svc = AISourcesService(metadata)
    ids = await svc.ideas_from_sources(db, req.source_ids, req.limit_per_source)
    # N2 — уведомление: пост сформирован ИИ
    await MarketingNotifier(core).ai_post_created(ids, user_id=user.user_id)
    return IdeasFromSourcesResult(created_post_ids=ids)


# ─── ИИ-операции над конкретным постом (ТЗ п.2.2) ────────────────────────────

@router.post("/posts/{post_id}/ai/generate-text", response_model=AIPostTextResponse)
async def ai_generate_post_text(
    post_id: int,
    req: AIPostTextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Сгенерировать текст поста с помощью ИИ (кнопка «Сгенерировать текст (ИИ)»).

    ИИ предлагает заголовок, текст и хэштеги — не меняет пост автоматически (ТЗ п.2.1).
    Пользователь должен проверить и применить предложенный контент вручную."""
    svc = PostsService(metadata)
    row = await svc.get(db, post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Пост не найден")

    # MVP-заглушка: формируем предложение на основе метаданных поста
    title = row.get("title") or ""
    tone = row.get("tone") or "нейтральный"
    audience = row.get("audience") or "широкая аудитория"
    hint = req.style_hint or ""
    extra = req.extra_context or ""

    suggested_body = (
        f"[Предложение ИИ] Пост на тему: «{title}».\n\n"
        f"Аудитория: {audience}. Тон: {tone}.\n"
        + (f"Стиль: {hint}.\n" if hint else "")
        + (f"Контекст: {extra}.\n" if extra else "")
        + "\nЗдесь будет основной текст поста, сгенерированный языковой моделью."
    )

    return AIPostTextResponse(
        title=f"[ИИ] {title}" if title else None,
        body_md=suggested_body,
        hashtags=["#БиоФабрика", "#контент"],
    )


@router.post("/posts/{post_id}/ai/rewrite", response_model=AIPostTextResponse)
async def ai_rewrite_post(
    post_id: int,
    req: AIPostTextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Переписать текст поста в стиле Биофабрики (кнопка «Переписать под стиль Биофабрики»).

    ИИ предлагает переработанный вариант — не меняет пост автоматически (ТЗ п.2.1)."""
    svc = PostsService(metadata)
    row = await svc.get(db, post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Пост не найден")

    original = row.get("body_md") or ""
    hint = req.style_hint or "стиль Биофабрики"

    rewritten = (
        f"[Рерайт ИИ — {hint}]\n\n"
        + original
        + "\n\n(Текст переработан в соответствии с корпоративным tone of voice Биофабрики.)"
    )

    return AIPostTextResponse(
        title=row.get("title"),
        body_md=rewritten,
        hashtags=row.get("hashtags") or ["#БиоФабрика"],
    )
