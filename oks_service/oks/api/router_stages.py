"""Роутер: этапы ОКС."""
from fastapi import APIRouter, Depends, HTTPException

from oks.api.deps import get_db, require, User
from oks.schemas.dto_stages import OksStageCreate, OksStageUpdate, OksStageOut
import oks.repositories.stages_repo as repo

router = APIRouter(tags=["Stages"])


@router.get("/objects/{object_id}/stages", response_model=list[OksStageOut])
def list_stages(
    object_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Список этапов объекта ОКС."""
    return [OksStageOut(**r) for r in repo.list_stages(db, object_id)]


@router.post("/objects/{object_id}/stages", response_model=OksStageOut, status_code=201)
def create_stage(
    object_id: int,
    body: OksStageCreate,
    db=Depends(get_db),
    _user: User = Depends(require("manage_stages")),
):
    """Создать этап для объекта ОКС."""
    row = repo.create_stage(db, object_id, body.model_dump(exclude_none=True))
    return OksStageOut(**row)


@router.get("/stages/{stage_id}", response_model=OksStageOut)
def get_stage(
    stage_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Карточка этапа ОКС."""
    row = repo.get_stage(db, stage_id)
    if not row:
        raise HTTPException(404, "Этап не найден")
    return OksStageOut(**row)


@router.patch("/stages/{stage_id}", response_model=OksStageOut)
def update_stage(
    stage_id: int,
    body: OksStageUpdate,
    db=Depends(get_db),
    _user: User = Depends(require("manage_stages")),
):
    """Обновить этап ОКС."""
    row = repo.update_stage(db, stage_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "Этап не найден")
    return OksStageOut(**row)


@router.delete("/stages/{stage_id}", status_code=204)
def delete_stage(
    stage_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("manage_stages")),
):
    """Удалить этап ОКС."""
    if not repo.delete_stage(db, stage_id):
        raise HTTPException(404, "Этап не найден")
