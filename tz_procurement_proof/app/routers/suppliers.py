
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.deps import get_db
from app import schemas
from app.models import ProcurementRequest, SupplierQuote, Event, StatusEnum
from app.services.workflow import set_status
from app.services.notifications import notify

router = APIRouter(prefix="/suppliers", tags=["Поставщики/КП"])

@router.post("/quotes")
def add_quote(payload: schemas.SupplierQuoteIn, db: Session = Depends(get_db)):
    req = db.get(ProcurementRequest, payload.request_id)
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    quote = SupplierQuote(
        request=req,
        supplier_name=payload.supplier_name,
        price=payload.price,
        delivery_days=payload.delivery_days,
        payment_terms=payload.payment_terms,
        comment=payload.comment,
        file_ref=payload.file_ref,
    )
    db.add(quote)
    db.commit()
    return {"ok": True, "quote_id": quote.id}


@router.get("/quotes/{request_id}", response_model=List[schemas.SupplierQuoteOut])
def list_quotes(request_id: int, db: Session = Depends(get_db)):
    return db.query(SupplierQuote).filter(SupplierQuote.request_id == request_id).all()


@router.post("/quotes/{quote_id}/select")
def select_winner(quote_id: int, db: Session = Depends(get_db)):
    """Выбрать победителя тендера.

    - Снимает флаг is_selected со всех КП по этой заявке.
    - Устанавливает is_selected=True для выбранного КП.
    - Переводит заявку в статус 'awaiting_delivery'.
    - Отправляет уведомление.
    """
    quote = db.get(SupplierQuote, quote_id)
    if not quote:
        raise HTTPException(404, "КП не найдено")

    # Снять выбор со всех КП по заявке
    db.query(SupplierQuote).filter(
        SupplierQuote.request_id == quote.request_id,
        SupplierQuote.is_selected == True,
    ).update({"is_selected": False})

    # Выбрать победителя
    quote.is_selected = True
    db.add(Event(
        request_id=quote.request_id,
        event_type="winner_selected",
        payload=f"supplier='{quote.supplier_name}', price={quote.price}, quote_id={quote.id}",
    ))

    # Перевести заявку в ожидание поставки
    req = db.get(ProcurementRequest, quote.request_id)
    if req and req.status == StatusEnum.in_progress:
        set_status(db, req, StatusEnum.awaiting_delivery, f"winner: {quote.supplier_name}")

    db.commit()

    notify(
        channel="procurement",
        message=f"Победитель КП выбран: {quote.supplier_name}, цена {quote.price} (заявка #{quote.request_id})",
    )
    return {"ok": True, "selected_quote_id": quote.id, "supplier": quote.supplier_name}
