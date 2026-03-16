from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db
from core.common.correlation import get_correlation_id
from core.common.audit import write_audit
import json

router = APIRouter()

class WfDefIn(BaseModel):
    code: str
    version: int
    steps: list[str]

@router.post("/workflow/definitions")
def create_definition(body: WfDefIn, db = Depends(get_db)):
    cfg = {"steps": body.steps}
    db.execute(text("INSERT INTO workflow_definitions(code, version, config_json, is_active) VALUES (:c,:v,:j,TRUE)"),
               {"c": body.code, "v": body.version, "j": json.dumps(cfg)})
    db.commit()
    return {"ok": True}

class WfInstIn(BaseModel):
    definition_id: int
    entity_type: str
    entity_id: str

@router.post("/workflow/instances")
def create_instance(body: WfInstIn, db = Depends(get_db), correlation_id: str = Depends(get_correlation_id)):
    r = db.execute(text("SELECT config_json FROM workflow_definitions WHERE id=:id AND is_active=TRUE"), {"id": body.definition_id}).mappings().first()
    if not r:
        raise HTTPException(404, "Определение не найдено/не активно")
    steps = json.loads(r["config_json"]).get("steps") or []
    initial = steps[0] if steps else "start"
    row = db.execute(text("INSERT INTO workflow_instances(definition_id, entity_type, entity_id, state, context_json, created_at) VALUES (:d,:t,:e,:s,:ctx,NOW()) RETURNING id"),
                     {"d": body.definition_id, "t": body.entity_type, "e": body.entity_id, "s": initial, "ctx": json.dumps({})}).first()
    inst_id = row[0]
    write_audit(db, actor_user_id=None, actor_system="system:workflow_api", action="workflow.create", resource="workflow_instance", resource_id=inst_id, diff_json="{}", correlation_id=correlation_id)
    return {"id": inst_id, "state": initial}

class WfAdvanceIn(BaseModel):
    action: str = "approve"
    comment: str | None = None

@router.post("/workflow/instances/{instance_id}/advance")
def advance(instance_id: int, body: WfAdvanceIn, db = Depends(get_db), correlation_id: str = Depends(get_correlation_id)):
    d = db.execute(text("SELECT wi.state, wd.config_json FROM workflow_instances wi JOIN workflow_definitions wd ON wi.definition_id = wd.id WHERE wi.id=:id"),
                   {"id": instance_id}).mappings().first()
    if not d:
        raise HTTPException(404, "Инстанс не найден")
    steps = json.loads(d["config_json"]).get("steps") or []
    cur = d["state"]
    if cur not in steps or steps.index(cur) == len(steps)-1:
        raise HTTPException(400, "Нельзя продвинуть дальше")
    new_state = steps[steps.index(cur)+1]
    db.execute(text("UPDATE workflow_instances SET state=:s WHERE id=:id"), {"s": new_state, "id": instance_id})
    db.execute(text("INSERT INTO workflow_history(instance_id, actor_user_id, action, comment, created_at) VALUES (:i, NULL, :a, :c, NOW())"),
               {"i": instance_id, "a": body.action, "c": body.comment})
    db.commit()
    write_audit(db, actor_user_id=None, actor_system="system:workflow_api", action="workflow.advance", resource="workflow_instance", resource_id=instance_id, diff_json=json.dumps({"from":cur,"to":new_state}), correlation_id=correlation_id)
    return {"id": instance_id, "state": new_state}
