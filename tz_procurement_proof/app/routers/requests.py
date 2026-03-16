
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.deps import get_db, get_current_user, CurrentUser
from app import schemas
from app.models import ProcurementRequest, RequestItem, StatusEnum, User, Event
from app.services.workflow import set_status
from app.services.notifications import notify_request_created, notify_status_changed

router = APIRouter(prefix="/requests", tags=["Заявки"])


@router.post("", response_model=schemas.ProcurementOut)
def create_request(
    payload: schemas.ProcurementCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создать заявку на закупку.

    Разрешено ролям: Инициатор, Начальник ОЗ, Исполнитель ОЗ.
    Инициатор определяется из заголовка X-User-Id.
    """
    current_user.require_role("Инициатор", "Начальник ОЗ", "Исполнитель ОЗ")

    # Ищем пользователя по ID из заголовка; если не найден — первый Инициатор в БД
    initiator = None
    if current_user.user_id:
        initiator = db.get(User, current_user.user_id)
    if not initiator:
        initiator = db.query(User).filter(User.role == "Инициатор").first()
    if not initiator:
        raise HTTPException(400, "Инициатор не найден — укажите X-User-Id")

    req = ProcurementRequest(
        subject=payload.subject,
        justification=payload.justification,
        initiator=initiator,
        status=StatusEnum.on_approval,
    )
    db.add(req)
    db.flush()
    for it in payload.items:
        db.add(RequestItem(
            request=req,
            nomenclature=it.nomenclature,
            tech_spec=it.tech_spec,
            due_days=it.due_days,
            quantity=it.quantity,
            justification=it.justification,
        ))
    db.add(Event(request=req, event_type="created", payload="request created"))
    db.commit()
    db.refresh(req)
    notify_request_created(req.id, req.subject)
    return req


@router.get("", response_model=List[schemas.ProcurementOut])
def list_requests(
    db: Session = Depends(get_db),
    status: StatusEnum | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Список заявок. Доступно всем аутентифицированным пользователям."""
    current_user.require_role(
        "Инициатор", "Склад", "Директор", "Начальник ОЗ", "Исполнитель ОЗ", "Юротдел", "Бухгалтерия"
    )
    q = db.query(ProcurementRequest)
    if status:
        q = q.filter(ProcurementRequest.status == status)
    return q.order_by(ProcurementRequest.id.desc()).all()


@router.get("/{req_id}", response_model=schemas.ProcurementOut)
def get_request(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    current_user.require_role(
        "Инициатор", "Склад", "Директор", "Начальник ОЗ", "Исполнитель ОЗ", "Юротдел", "Бухгалтерия"
    )
    req = db.get(ProcurementRequest, req_id)
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    return req


@router.patch("/{req_id}/status", response_model=schemas.ProcurementOut)
def patch_status(
    req_id: int,
    payload: schemas.StatusPatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Изменить статус заявки. Разрешено: Начальник ОЗ, Директор, Исполнитель ОЗ."""
    current_user.require_role("Начальник ОЗ", "Директор", "Исполнитель ОЗ")
    req = db.get(ProcurementRequest, req_id)
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    old_status = req.status.value
    updated = set_status(db, req, payload.status, payload.status.value)
    notify_status_changed(req_id, old_status, payload.status.value)
    return updated
