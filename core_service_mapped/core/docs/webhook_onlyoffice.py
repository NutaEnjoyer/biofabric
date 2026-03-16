from fastapi import APIRouter, Request, HTTPException, Depends
import hmac, hashlib
from sqlalchemy import text
from core.config import settings
from core.db import get_db
from core.common.logging import log

router = APIRouter()

@router.post("/docs/webhook")
async def onlyoffice_webhook(request: Request, db = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("Authorization") or ""
    calc = "Bearer " + hmac.new(settings.ONLYOFFICE_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, calc):
        raise HTTPException(status_code=401, detail="Неверная подпись вебхука")
    payload = await request.json()
    doc_id = str(payload.get("key") or payload.get("doc_id"))
    version_no = int(payload.get("version") or payload.get("history",{}).get("serverVersion", 0))
    # Идемпотентность
    already = db.execute(text("SELECT 1 FROM document_versions WHERE document_id=:d AND version_no=:v"), {"d": doc_id, "v": version_no}).first()
    if already:
        log("INFO", "oo.webhook.duplicate", doc_id=doc_id, version_no=version_no)
        return {"ok": True, "duplicate": True}
    file_path = payload.get("url") or payload.get("file") or ""
    db.execute(text("INSERT INTO document_versions(document_id, version_no, file_path, created_at) VALUES (:d,:v,:p,NOW())"),
               {"d": doc_id, "v": version_no, "p": file_path})
    db.commit()
    log("INFO", "oo.webhook.saved", doc_id=doc_id, version_no=version_no)
    return {"ok": True}
