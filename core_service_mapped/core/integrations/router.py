from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db
import json

router = APIRouter()

class EndpointIn(BaseModel):
    type: str
    name: str
    base_url: str
    creds_json: dict | None = None

@router.post("/integrations/endpoints")
def create_endpoint(body: EndpointIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO integration_endpoints(type, name, base_url, creds_json, is_active, created_at) VALUES (:t,:n,:u,:c,TRUE,NOW())"),
               {"t": body.type, "n": body.name, "u": body.base_url, "c": json.dumps(body.creds_json or {})})
    db.commit()
    return {"ok": True}

class ProxyIn(BaseModel):
    name: str
    type: str
    host: str
    port: int
    protocol: str = "https"
    auth_json: dict | None = None

@router.post("/integrations/proxy/endpoints")
def create_proxy(body: ProxyIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO proxy_endpoints(name, type, host, port, protocol, auth_json, is_active, health, last_check_at) VALUES (:n,:t,:h,:p,:pr,:a,TRUE,'unknown',NOW())"),
               {"n": body.name, "t": body.type, "h": body.host, "p": body.port, "pr": body.protocol, "a": json.dumps(body.auth_json or {})})
    db.commit()
    return {"ok": True}
