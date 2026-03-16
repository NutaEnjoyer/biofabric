from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import metadata
from ..api.deps import get_db, get_user, get_core, can
from ..schemas.dto_posts import PostCreate, PostUpdate, PostRead, PublishNowRequest, PublishNowResponse, ReplacePostRequest
from ..schemas.dto_common import ResponseOk
from ..services.posts import PostsService
from ..services.publishing import PublishingService
from ..services.workflow import WorkflowService
from ..services.documents import DocumentsService
from ..services.notifier import MarketingNotifier

router = APIRouter()


@router.post("/posts", response_model=ResponseOk)
async def create_post(
    payload: PostCreate,
    db: AsyncSession = Depends(get_db),
    core=Depends(get_core),
    user=Depends(get_user),
):
    """Создать черновик поста.

    Для чего: ручное добавление поста или добавление ИИ-сгенерированного контента без дат.
    Если переданы document_ids — привязывает документы ООК к посту."""
    if not can(user, "create_post", "post"):
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания поста")
    svc = PostsService(metadata)
    pid = await svc.create_draft(db, payload.model_dump(exclude={"document_ids"}))
    # привязываем документы ООК (если переданы)
    if payload.document_ids:
        doc_svc = DocumentsService(core)
        for doc_id in payload.document_ids:
            await doc_svc.bind("mk_post", str(pid), doc_id)
    return ResponseOk(data={"post_id": pid})


@router.get("/posts/{post_id}", response_model=ResponseOk)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Получить карточку поста по ID (метаданные + контент)."""
    svc = PostsService(metadata)
    row = await svc.get(db, post_id)
    return ResponseOk(data=row)


@router.get("/posts", response_model=ResponseOk)
async def list_posts(
    period_from: str | None = None,
    period_to: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Список постов за период (или все, если период не указан)."""
    svc = PostsService(metadata)
    rows = await svc.repo.list_posts(db, period_from, period_to)
    return ResponseOk(data=rows)


@router.patch("/posts/{post_id}", response_model=ResponseOk)
async def update_post(
    post_id: int,
    payload: PostUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_user),
):
    """Обновить карточку поста: текст/мета/дата."""
    if not can(user, "update_post", "post"):
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования поста")
    svc = PostsService(metadata)
    await svc.update(db, post_id, payload.model_dump(exclude_none=True))
    return ResponseOk()


@router.post("/posts/{post_id}/status/{status}", response_model=ResponseOk)
async def set_status(
    post_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    core=Depends(get_core),
):
    """Поменять статус поста.

    Использование: draft→in_review, in_review→approved, approved→published и т.д."""
    svc = PostsService(metadata)
    await svc.set_status(db, post_id, status)
    # также отправим сигнал в ядро (если доступно)
    wf = WorkflowService(core)
    await wf.advance("mk_post", str(post_id), f"to_{status}")
    # N4 — уведомление при утверждении поста
    if status == "approved":
        user = await get_user()
        await MarketingNotifier(core).post_approved(post_id, author_user_id=user.user_id)
    return ResponseOk()


@router.post("/posts/{post_id}/date", response_model=ResponseOk)
async def set_date(post_id: int, ymd: str, db: AsyncSession = Depends(get_db)):
    """Назначить дату публикации (без времени)."""
    svc = PostsService(metadata)
    await svc.set_date(db, post_id, ymd)
    return ResponseOk()


@router.post("/posts/{post_id}/publish", response_model=PublishNowResponse)
async def publish_now(
    post_id: int,
    payload: PublishNowRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_user),
):
    """Опубликовать пост «сейчас» в выбранную платформу (TG/VK).

    После успеха проставляем `published` и сохраняем ссылку."""
    if not can(user, "publish", "post"):
        raise HTTPException(status_code=403, detail="Недостаточно прав для публикации поста")
    svc = PostsService(metadata)
    row = await svc.get(db, post_id)
    if not row:
        return PublishNowResponse(ok=False, error_message="Пост не найден")
    # body_md — каноничное поле контента (mk_post_contents.body_md)
    text = row.get("body_md") or ""
    pub = PublishingService()
    try:
        if payload.platform == "tg":
            url = await pub.publish_now_tg(text)
        else:
            url = await pub.publish_now_vk(text)
        await svc.set_external_url(db, post_id, url)
        await svc.set_status(db, post_id, "published")
        return PublishNowResponse(ok=True, external_url=url)
    except Exception as exc:
        # Ошибка публикации не меняет контент и статус поста (ТЗ п.5)
        return PublishNowResponse(ok=False, error_message=str(exc))


@router.post("/posts/replace", response_model=ResponseOk)
async def replace_post(req: ReplacePostRequest, db: AsyncSession = Depends(get_db)):
    """Заменить пост на указанную дату другой идеей из корзины.

    Снимаем дату со старого поста и назначаем её идее."""
    svc = PostsService(metadata)
    new_pid = await svc.replace_post_in_plan(
        db, req.date, req.post_id_to_remove, req.idea_post_id_to_use
    )
    return ResponseOk(data={"post_id": new_pid})
