"""Роутер: комментарии ОКС."""
from fastapi import APIRouter, Depends, HTTPException

from oks.api.deps import get_db, require, User
from oks.schemas.dto_comments import OksCommentCreate, OksCommentOut
import oks.repositories.comments_repo as repo

router = APIRouter(tags=["Comments"])


@router.get("/objects/{object_id}/comments", response_model=list[OksCommentOut])
def list_comments(
    object_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Список комментариев объекта ОКС."""
    return [OksCommentOut(**r) for r in repo.list_comments(db, object_id)]


@router.post("/objects/{object_id}/comments", response_model=OksCommentOut, status_code=201)
def create_comment(
    object_id: int,
    body: OksCommentCreate,
    db=Depends(get_db),
    user: User = Depends(require("add_comment")),
):
    """Добавить комментарий к объекту ОКС (или к конкретному этапу)."""
    row = repo.create_comment(db, object_id, body.text, user.user_id, body.stage_id)
    return OksCommentOut(**row)
