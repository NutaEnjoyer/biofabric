
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.deps import get_db, get_current_user, CurrentUser
from app import schemas
from app.models import ProcurementRequest, Document

router = APIRouter(prefix="/documents", tags=["Документы"])


@router.post("")
def add_document(
    payload: schemas.DocumentIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Прикрепить документ к заявке. Разрешено: Исполнитель ОЗ, Начальник ОЗ, Юротдел, Бухгалтерия."""
    current_user.require_role("Исполнитель ОЗ", "Начальник ОЗ", "Юротдел", "Бухгалтерия")
    req = db.get(ProcurementRequest, payload.request_id)
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    doc = Document(
        request=req,
        doc_type=payload.doc_type,
        filename=payload.filename,
        storage_url=payload.storage_url,
        signed=payload.signed,
    )
    db.add(doc)
    db.commit()
    return {"ok": True, "document_id": doc.id}


@router.get("/{request_id}", response_model=List[dict])
def list_documents(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    current_user.require_role(
        "Инициатор", "Склад", "Директор", "Начальник ОЗ", "Исполнитель ОЗ", "Юротдел", "Бухгалтерия"
    )
    docs = db.query(Document).filter(Document.request_id == request_id).all()
    return [{
        "id": d.id, "doc_type": d.doc_type, "filename": d.filename,
        "storage_url": d.storage_url, "signed": d.signed,
    } for d in docs]
