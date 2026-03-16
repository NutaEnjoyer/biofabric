from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db
import json

router = APIRouter()

class TemplateIn(BaseModel):
    code: str
    channel: str
    subject_tpl: str | None = None
    body_tpl: str

@router.post("/notifications/templates")
def create_template(body: TemplateIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO notification_templates(code, channel, subject_tpl, body_tpl, locale, is_active) VALUES (:c,:ch,:s,:b,'ru',TRUE)"),
               {"c": body.code, "ch": body.channel, "s": body.subject_tpl, "b": body.body_tpl})
    db.commit()
    return {"ok": True}

class SendIn(BaseModel):
    template_code: str
    to: list[str]
    payload: dict

@router.post("/notifications/send")
def send(body: SendIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO notifications_outbox(template_code, to_json, payload_json, status, attempts, created_at) VALUES (:t,:to,:p,'pending',0,NOW())"),
               {"t": body.template_code, "to": json.dumps(body.to), "p": json.dumps(body.payload)})
    db.commit()
    return {"queued": True}
