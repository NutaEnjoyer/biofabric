"""Клиент Core Service для модуля карантинирования животных.

Отправляет события и уведомления в ядро ERP через HTTP.
При недоступности ядра — логирует ошибку, не блокирует операцию.
"""
import logging
import os
import httpx
from typing import Optional

logger = logging.getLogger("quarantine.core_client")

CORE_URL = os.environ.get("CORE_SERVICE_URL", "http://core_service:8000")


def _post(path: str, payload: dict) -> dict:
    """Отправить POST-запрос в Core Service. При ошибке — логировать и вернуть {'ok': False}."""
    try:
        resp = httpx.post(f"{CORE_URL}{path}", json=payload, timeout=3.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("core_client: %s failed: %s", path, exc)
        return {"ok": False, "error": str(exc)}


# ─── Уведомления ────────────────────────────────────────────────────────────

def notify(event_type: str, message: str, user_id: Optional[int] = None, meta: Optional[dict] = None) -> dict:
    """Отправить уведомление через Core Service (POST /v1/core/notifications/send)."""
    return _post("/v1/core/notifications/send", {
        "user_id": user_id,
        "event_type": event_type,
        "message": message,
        "meta": meta or {},
    })


def notify_operation_saved(entry_ids: list[int], op_type: str, user_id: Optional[int] = None) -> dict:
    """Уведомление: операция успешно сохранена."""
    ids_str = ", ".join(str(i) for i in entry_ids)
    return notify(
        event_type="quarantine.operation_saved",
        message=f"Операция '{op_type}' сохранена (записи: {ids_str})",
        user_id=user_id,
        meta={"entry_ids": entry_ids, "op_type": op_type},
    )


def notify_movement(entry_out_id: int, entry_in_id: int, user_id: Optional[int] = None) -> dict:
    """Уведомление: выполнено перемещение животных."""
    return notify(
        event_type="quarantine.movement",
        message=f"Перемещение выполнено (out: {entry_out_id}, in: {entry_in_id})",
        user_id=user_id,
        meta={"entry_out_id": entry_out_id, "entry_in_id": entry_in_id},
    )


def notify_validation_error(message: str, user_id: Optional[int] = None) -> dict:
    """Уведомление: ошибка валидации при вводе данных."""
    return notify(
        event_type="quarantine.validation_error",
        message=f"Ошибка ввода: {message}",
        user_id=user_id,
    )


# ─── Аудит и workflow ────────────────────────────────────────────────────────

def audit_log(entity_type: str, entity_id: str, action: str, payload: dict) -> dict:
    """Записать действие в аудит-лог Core Service."""
    return _post("/v1/core/audit/log", {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "meta": payload,
    })


def workflow_approve(entity_type: str, entity_id: str, approver: str) -> dict:
    """Продвинуть workflow через Core Service."""
    return _post("/v1/core/workflow/advance", {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "transition": f"approve_by_{approver}",
    })


def workflow_archive_month(year: int, month: int) -> dict:
    """Уведомить ядро о закрытии периода."""
    return notify(
        event_type="quarantine.month_archived",
        message=f"Период {year}-{month:02d} закрыт и архивирован",
        meta={"year": year, "month": month},
    )
