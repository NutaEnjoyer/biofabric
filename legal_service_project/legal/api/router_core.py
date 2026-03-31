"""Core API — межсервисные эндпоинты.

Другие сервисы (marketing, quarantine, procurement) шлют сюда:
  - уведомления  POST /v1/core/notifications/send
  - workflow     POST /v1/core/workflow/advance
  - документы    POST /v1/core/docs/bind
  - аудит        POST /v1/core/audit/log

Реализация: пишем напрямую в таблицы общей БД.
"""
from __future__ import annotations
import json
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Optional
from legal.api.deps import get_db

logger = logging.getLogger("core")
router = APIRouter()


class NotifyRequest(BaseModel):
    user_id: Optional[int] = None
    event_type: str
    message: str
    meta: Optional[dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    entity_type: str
    entity_id: str
    transition: str


class BindDocRequest(BaseModel):
    entity_type: str
    entity_id: str
    document_id: int


class AuditRequest(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    meta: Optional[dict[str, Any]] = None


@router.post("/notifications/send")
def send_notification(req: NotifyRequest, conn=Depends(get_db)):
    """Записать уведомление в notifications_outbox."""
    to_json = json.dumps([str(req.user_id)] if req.user_id else [])
    payload = json.dumps({"message": req.message, **(req.meta or {})})
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO notifications_outbox
                (template_code, to_json, payload_json, status, updated_at)
            VALUES (%s, %s::jsonb, %s::jsonb, 'pending', NOW())
            """,
            (req.event_type, to_json, payload),
        )
        conn.commit()
    except Exception:
        logger.exception("notifications_outbox insert failed, fallback to log")
        logger.info("NOTIFY user=%s event=%s msg=%s", req.user_id, req.event_type, req.message[:120])
    return {"ok": True}


@router.post("/workflow/advance")
def advance_workflow(req: WorkflowRequest, conn=Depends(get_db)):
    """Обновить состояние workflow и записать историю."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, state FROM workflow_instances WHERE entity_type=%s AND entity_id=%s ORDER BY id DESC LIMIT 1",
            (req.entity_type, req.entity_id),
        )
        row = cur.fetchone()
        if row:
            instance_id, current_state = row
            cur.execute(
                "UPDATE workflow_instances SET state=%s WHERE id=%s",
                (req.transition, instance_id),
            )
            cur.execute(
                """
                INSERT INTO workflow_history(instance_id, actor_user_id, action, comment, created_at)
                VALUES (%s, NULL, %s, NULL, NOW())
                """,
                (instance_id, req.transition),
            )
        else:
            # Инстанса нет — фиксируем в аудите
            cur.execute(
                """
                INSERT INTO audit_log(actor_system, action, resource, resource_id, diff_json, created_at)
                VALUES ('system:router_core', %s, %s, %s, %s::jsonb, NOW())
                """,
                (
                    f"workflow.{req.transition}",
                    req.entity_type,
                    req.entity_id,
                    json.dumps({"transition": req.transition}),
                ),
            )
        conn.commit()
    except Exception:
        logger.exception("workflow advance failed, fallback to log")
        logger.info("WORKFLOW %s/%s → %s", req.entity_type, req.entity_id, req.transition)
    return {"ok": True}


@router.post("/docs/bind")
def bind_document(req: BindDocRequest, conn=Depends(get_db)):
    """Привязать документ к сущности через document_bindings."""
    try:
        object_id = int(req.entity_id) if req.entity_id.isdigit() else None
        if object_id is not None:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO document_bindings(document_id, object_type, object_id, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (document_id, object_type, object_id, purpose) DO NOTHING
                """,
                (req.document_id, req.entity_type, object_id),
            )
            conn.commit()
        else:
            logger.warning("docs/bind: entity_id '%s' не является числом, пропускаем", req.entity_id)
    except Exception:
        logger.exception("document_bindings insert failed, fallback to log")
        logger.info("DOCS bind %s/%s doc=%s", req.entity_type, req.entity_id, req.document_id)
    return {"ok": True}


@router.post("/audit/log")
def audit_log_endpoint(req: AuditRequest, conn=Depends(get_db)):
    """Записать событие в audit_log."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log(actor_system, action, resource, resource_id, diff_json, created_at)
            VALUES ('system:router_core', %s, %s, %s, %s::jsonb, NOW())
            """,
            (
                req.action,
                req.entity_type,
                req.entity_id,
                json.dumps(req.meta or {}),
            ),
        )
        conn.commit()
    except Exception:
        logger.exception("audit_log insert failed, fallback to log")
        logger.info("AUDIT %s %s/%s", req.action, req.entity_type, req.entity_id)
    return {"ok": True}
