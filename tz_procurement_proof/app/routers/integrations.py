
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models import ProcurementRequest, StatusEnum, OneCStatusEnum, Event
from app.services.workflow import set_status
from app.services.notifications import notify_1c_sent

router = APIRouter(prefix="/integrations", tags=["Интеграции"])


@router.post("/1c/webhook/stock-received/{request_id}")
def webhook_stock_received(request_id: int, db: Session = Depends(get_db)):
    """Входящий webhook от 1С: товар получен на склад → заявка переводится в 'Исполнена'."""
    req = db.get(ProcurementRequest, request_id)
    if not req:
        return {"ok": False, "error": "not found"}
    set_status(db, req, StatusEnum.done, "1C: stock received")
    req.onec_status = OneCStatusEnum.sent
    db.commit()
    return {"ok": True}


@router.post("/1c/send/{request_id}", summary="Отправить заявку в 1С (исходящая интеграция)")
def send_to_1c(request_id: int, db: Session = Depends(get_db)):
    """Поставить заявку в очередь исходящей отправки в 1С.

    Логика:
    - Если уже отправлена (sent) — идемпотентный ответ.
    - Если в очереди (queued) — сообщить статус.
    - Иначе — перевести в queued и создать событие.

    В MVP очередь имитируется статусом onec_status.
    В prod здесь ставится задача в Celery/RabbitMQ.
    """
    req = db.get(ProcurementRequest, request_id)
    if not req:
        return {"ok": False, "error": "Заявка не найдена"}

    if req.onec_status == OneCStatusEnum.sent:
        return {"ok": True, "onec_status": "sent", "message": "Уже отправлена в 1С"}

    if req.onec_status == OneCStatusEnum.queued:
        return {"ok": True, "onec_status": "queued", "message": "Уже в очереди на отправку"}

    req.onec_status = OneCStatusEnum.queued
    db.add(Event(
        request_id=request_id,
        event_type="onec_queued",
        payload=f"request #{request_id} queued for 1C export",
    ))
    db.commit()

    notify_1c_sent(request_id, "queued")
    return {"ok": True, "onec_status": "queued", "message": "Заявка поставлена в очередь 1С"}
