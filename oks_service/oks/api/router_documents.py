"""Роутер: документы ОКС."""
from fastapi import APIRouter, Depends, HTTPException

from oks.api.deps import get_db, get_db_tx, require, User
from oks.schemas.dto_documents import OksDocCreate, OksDocUpdate, OksDocOut
import oks.repositories.documents_repo as repo

router = APIRouter(tags=["Documents"])


@router.get("/objects/{object_id}/documents", response_model=list[OksDocOut])
def list_documents(
    object_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Список документов объекта ОКС."""
    return [OksDocOut(**r) for r in repo.list_documents(db, object_id)]


@router.post("/objects/{object_id}/documents", response_model=OksDocOut, status_code=201)
def create_document(
    object_id: int,
    body: OksDocCreate,
    db=Depends(get_db_tx),
    user: User = Depends(require("manage_documents")),
):
    """Прикрепить документ к объекту ОКС.

    Создаёт запись в `documents` (ООК) и в `oks_documents`.
    Транзакция: если что-то упало — откат обоих INSERT.
    """
    try:
        row = repo.create_document(db, object_id, body.model_dump(exclude_none=True), user.user_id)
        db.commit()
        return OksDocOut(**row)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Ошибка создания документа: {e}")


@router.patch("/documents/{oks_doc_id}", response_model=OksDocOut)
def update_document(
    oks_doc_id: int,
    body: OksDocUpdate,
    db=Depends(get_db),
    _user: User = Depends(require("manage_documents")),
):
    """Обновить статус / тип документа ОКС."""
    row = repo.update_document(db, oks_doc_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "Документ не найден")
    return OksDocOut(**row)


@router.delete("/documents/{oks_doc_id}", status_code=204)
def delete_document(
    oks_doc_id: int,
    db=Depends(get_db),
    _user: User = Depends(require("manage_documents")),
):
    """Удалить привязку документа ОКС."""
    if not repo.delete_document(db, oks_doc_id):
        raise HTTPException(404, "Документ не найден")
