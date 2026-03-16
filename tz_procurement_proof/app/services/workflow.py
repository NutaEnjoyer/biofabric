
from sqlalchemy.orm import Session
from app.models import ProcurementRequest, StatusEnum, Event

def set_status(db: Session, req: ProcurementRequest, status: StatusEnum, payload: str = ""):
    req.status = status
    db.add(Event(request=req, event_type="status_changed", payload=payload))
    db.commit()
    db.refresh(req)
    return req
