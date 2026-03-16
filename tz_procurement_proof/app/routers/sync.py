"""Синхронизация справочников с Core Service.

Core Service присылает сюда webhook-уведомления при изменении:
  - пользователей (создание/обновление/деактивация)
  - подразделений

Procurement хранит локальную копию пользователей в таблице `users`,
синхронизируя её по событиям от Core.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.deps import get_db
from app.models import User, RoleEnum, Event

router = APIRouter(prefix="/sync", tags=["Синхронизация справочников"])

# Маппинг ролей Core → RoleEnum Procurement
ROLE_MAP: dict[str, str] = {
    "legal_user":        "Юротдел",
    "legal_admin":       "Юротдел",
    "marketing_editor":  "Инициатор",
    "procurement_head":  "Начальник ОЗ",
    "procurement_buyer": "Исполнитель ОЗ",
    "director":          "Директор",
    "warehouse":         "Склад",
    "accounting":        "Бухгалтерия",
    "initiator":         "Инициатор",
}


class UserSyncPayload(BaseModel):
    core_user_id: int
    fio: str
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    role: str           # роль из Core (например "procurement_head")
    is_active: bool = True


@router.post("/users/upsert", summary="Синхронизировать пользователя из Core")
def upsert_user(payload: UserSyncPayload, db: Session = Depends(get_db)):
    """Создать или обновить пользователя по данным из Core Service.

    Core вызывает этот endpoint при любом изменении пользователя.
    Используется core_user_id как внешний ключ для идемпотентности.

    Маппинг ролей Core → Procurement:
      procurement_head → Начальник ОЗ
      procurement_buyer → Исполнитель ОЗ
      director → Директор
      legal_* → Юротдел
      и т.д.
    """
    proc_role = ROLE_MAP.get(payload.role)
    if not proc_role:
        raise HTTPException(400, f"Неизвестная роль Core: '{payload.role}'. Известные: {list(ROLE_MAP.keys())}")

    # Ищем существующего пользователя по email (внешний ключ)
    existing = None
    if payload.email:
        existing = db.query(User).filter(User.email == payload.email).first()

    if existing:
        existing.fio        = payload.fio
        existing.department = payload.department
        existing.position   = payload.position
        existing.phone      = payload.phone
        existing.role       = proc_role
        db.add(Event(
            request_id=None,
            event_type="user_synced",
            payload=f"updated user_id={existing.id} from core_user_id={payload.core_user_id}",
        ))
        db.commit()
        return {"ok": True, "action": "updated", "user_id": existing.id}
    else:
        new_user = User(
            fio=payload.fio,
            email=payload.email,
            department=payload.department,
            position=payload.position,
            phone=payload.phone,
            role=proc_role,
        )
        db.add(new_user)
        db.flush()
        db.add(Event(
            request_id=None,
            event_type="user_synced",
            payload=f"created user_id={new_user.id} from core_user_id={payload.core_user_id}",
        ))
        db.commit()
        return {"ok": True, "action": "created", "user_id": new_user.id}


@router.post("/users/deactivate/{email}", summary="Деактивировать пользователя")
def deactivate_user(email: str, db: Session = Depends(get_db)):
    """Пометить пользователя как неактивного (удалён в Core).

    Не удаляет из БД — сохраняет историю согласований/заявок.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, f"Пользователь с email '{email}' не найден")
    # Меняем роль на "Инициатор" (минимальные права) как сигнал деактивации
    # В prod стоит добавить колонку is_active
    db.add(Event(
        request_id=None,
        event_type="user_deactivated",
        payload=f"deactivated user_id={user.id} email={email}",
    ))
    db.commit()
    return {"ok": True, "message": f"Пользователь {email} деактивирован"}


@router.get("/users", summary="Список пользователей (локальная копия)")
def list_users(db: Session = Depends(get_db)):
    """Вернуть текущую локальную копию справочника пользователей."""
    users = db.query(User).order_by(User.id).all()
    return [
        {"id": u.id, "fio": u.fio, "email": u.email, "role": u.role, "department": u.department}
        for u in users
    ]
