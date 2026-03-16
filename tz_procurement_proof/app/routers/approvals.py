
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user, CurrentUser
from app import schemas
from app.models import ProcurementRequest, Approval, User, ApprovalDecisionEnum, StatusEnum
from app.services.workflow import set_status
from app.services.notifications import notify_approved

router = APIRouter(prefix="/approvals", tags=["Согласование"])


@router.post("")
def approve(
    payload: schemas.ApprovalIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Вынести решение по заявке.

    Разрешено ролям: Директор, Юротдел, Начальник ОЗ.
    """
    current_user.require_role("Директор", "Юротдел", "Начальник ОЗ")

    req = db.get(ProcurementRequest, payload.request_id)
    if not req:
        raise HTTPException(404, "Заявка не найдена")

    # Используем user_id из заголовка если не передан явно в теле
    approver_id = payload.user_id or current_user.user_id
    user = db.get(User, approver_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    approval = Approval(request=req, user=user, decision=payload.decision, comment=payload.comment)
    db.add(approval)
    # простой маршрут: если директор или юротдел утвердили — переводим дальше
    if payload.decision == ApprovalDecisionEnum.approve and user.role in ("Директор", "Юротдел"):
        set_status(db, req, StatusEnum.in_progress, f"approved by {user.role}")
    db.commit()
    notify_approved(payload.request_id, user.fio, payload.decision.value)
    return {"ok": True}
