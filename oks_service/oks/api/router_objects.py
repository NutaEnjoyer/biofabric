"""Роутер: объекты ОКС (CRUD + иерархия)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from oks.api.deps import get_db, require, User
from oks.schemas.dto_objects import OksObjectCreate, OksObjectUpdate, OksObjectOut
import oks.repositories.objects_repo as repo

router = APIRouter(tags=["Objects"])


@router.get("/objects", response_model=list[OksObjectOut])
def list_objects(
    flat: bool = Query(False, description="true — все объекты без фильтрации по родителю"),
    parent_object_id: Optional[int] = Query(None),
    status_code: Optional[str] = Query(None),
    initiator_user_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Список объектов ОКС. По умолчанию — только корневые (без родителя)."""
    rows = repo.list_objects(
        db,
        flat=flat,
        parent_object_id=parent_object_id,
        status_code=status_code,
        initiator_user_id=initiator_user_id,
        search=search,
    )
    return [OksObjectOut(**r) for r in rows]


@router.post("/objects", response_model=OksObjectOut, status_code=201)
def create_object(
    body: OksObjectCreate,
    db=Depends(get_db),
    user: User = Depends(require("create_object")),
):
    """Создать объект ОКС."""
    data = body.model_dump(exclude_none=True)
    if "owner_user_id" not in data and user.user_id:
        data["owner_user_id"] = user.user_id
    row = repo.create_object(db, data)
    return OksObjectOut(**row)


@router.get("/objects/{object_id}", response_model=OksObjectOut)
def get_object(
    object_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Карточка объекта ОКС с кол-вом дочерних объектов и этапов."""
    row = repo.get_object(db, object_id)
    if not row:
        raise HTTPException(404, "Объект не найден")
    return OksObjectOut(**row)


@router.get("/objects/{object_id}/children", response_model=list[OksObjectOut])
def get_children(
    object_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Дочерние объекты (один уровень вложенности)."""
    rows = repo.list_objects(db, parent_object_id=object_id)
    return [OksObjectOut(**r) for r in rows]


@router.patch("/objects/{object_id}", response_model=OksObjectOut)
def update_object(
    object_id: int,
    body: OksObjectUpdate,
    db=Depends(get_db),
    _user: User = Depends(require("edit_object")),
):
    """Обновить объект ОКС."""
    row = repo.update_object(db, object_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "Объект не найден")
    return OksObjectOut(**row)


@router.delete("/objects/{object_id}", status_code=204)
def delete_object(
    object_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("delete_object")),
):
    """Удалить объект ОКС. Нельзя удалить, если есть дочерние объекты."""
    ok = repo.delete_object(db, object_id)
    if ok is False:
        raise HTTPException(409, "Нельзя удалить объект с дочерними объектами")
    if ok is None:
        raise HTTPException(404, "Объект не найден")
