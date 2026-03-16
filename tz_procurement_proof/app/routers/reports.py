"""Отчёты и экспорт данных Procurement."""
import csv
from io import StringIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.deps import get_db
from app.models import ProcurementRequest, StatusEnum, STATUS_COLOR

router = APIRouter(prefix="/reports", tags=["Отчёты"])


@router.get("/summary", summary="Сводка по статусам заявок")
def status_summary(db: Session = Depends(get_db)):
    """Количество заявок в каждом статусе с цветовой индикацией."""
    rows = (
        db.query(ProcurementRequest.status, func.count(ProcurementRequest.id))
        .group_by(ProcurementRequest.status)
        .all()
    )
    return [
        {
            "status": status.value,
            "count": count,
            "color": STATUS_COLOR.get(status, "grey"),
        }
        for status, count in rows
    ]


@router.get("/export/csv", summary="Экспорт заявок в CSV")
def export_csv(status: StatusEnum | None = None, db: Session = Depends(get_db)):
    """Экспортировать список заявок в CSV-файл.

    Опционально фильтр по статусу: ?status=На+согласовании
    """
    q = db.query(ProcurementRequest)
    if status:
        q = q.filter(ProcurementRequest.status == status)
    requests = q.order_by(ProcurementRequest.id).all()

    output = StringIO()
    fieldnames = ["id", "subject", "justification", "status", "onec_status", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in requests:
        writer.writerow({
            "id": r.id,
            "subject": r.subject,
            "justification": r.justification or "",
            "status": r.status.value,
            "onec_status": r.onec_status.value if r.onec_status else "not_sent",
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    output.seek(0)
    filename = f"procurement_requests{'_' + status.value if status else ''}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
