"""Сервис уведомлений Procurement.

Отправляет события в Core Service через HTTP.
При недоступности ядра — логирует ошибку, не блокирует операцию.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger("procurement.notifications")

CORE_URL = os.environ.get("CORE_SERVICE_URL", "http://core_service:8000")


def notify(channel: str, message: str, user_id: Optional[int] = None, meta: Optional[dict] = None) -> bool:
    """Отправить уведомление через Core Service.

    Возвращает True при успехе, False при ошибке (операция не прерывается).
    """
    try:
        import httpx
        payload = {
            "user_id": user_id,
            "event_type": f"procurement.{channel}",
            "message": message,
            "meta": meta or {},
        }
        resp = httpx.post(
            f"{CORE_URL}/v1/core/notifications/send",
            json=payload,
            timeout=3.0,
        )
        resp.raise_for_status()
        logger.info("notify sent: [%s] %s", channel, message)
        return True
    except Exception as exc:
        logger.warning("notify failed [%s]: %s | %s", channel, message, exc)
        return False


def notify_request_created(request_id: int, subject: str) -> None:
    notify("request_created", f"Создана заявка #{request_id}: «{subject}»", meta={"request_id": request_id})


def notify_status_changed(request_id: int, old_status: str, new_status: str) -> None:
    notify(
        "status_changed",
        f"Заявка #{request_id}: статус изменён «{old_status}» → «{new_status}»",
        meta={"request_id": request_id, "old_status": old_status, "new_status": new_status},
    )


def notify_approved(request_id: int, approver: str, decision: str) -> None:
    notify(
        "approval",
        f"Заявка #{request_id}: решение «{decision}» от {approver}",
        meta={"request_id": request_id, "approver": approver, "decision": decision},
    )


def notify_1c_sent(request_id: int, status: str) -> None:
    notify(
        "onec_integration",
        f"Заявка #{request_id}: статус отправки в 1С — {status}",
        meta={"request_id": request_id, "onec_status": status},
    )
