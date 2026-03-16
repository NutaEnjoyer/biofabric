"""Стаб «Core API» — внутренние эндпоинты для межсервисного взаимодействия.

Другие сервисы (marketing, quarantine, procurement) шлют сюда:
  - уведомления  POST /v1/core/notifications/send
  - workflow     POST /v1/core/workflow/advance
  - документы    POST /v1/core/docs/bind
  - аудит        POST /v1/core/audit/log

MVP: принимаем запросы, логируем и возвращаем {ok: true}.
Реальная реализация — уведомления через БД/WebSocket — следующий этап.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

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
async def send_notification(req: NotifyRequest):
    """Принять уведомление от внутреннего сервиса (MVP — только лог)."""
    logger.info(
        "NOTIFY user=%s event=%s msg=%s",
        req.user_id, req.event_type, req.message[:120]
    )
    return {"ok": True}


@router.post("/workflow/advance")
async def advance_workflow(req: WorkflowRequest):
    """Stub workflow transition (MVP)."""
    logger.info("WORKFLOW %s/%s → %s", req.entity_type, req.entity_id, req.transition)
    return {"ok": True}


@router.post("/docs/bind")
async def bind_document(req: BindDocRequest):
    """Stub document bind (MVP)."""
    logger.info("DOCS bind %s/%s doc=%s", req.entity_type, req.entity_id, req.document_id)
    return {"ok": True}


@router.post("/audit/log")
async def audit_log(req: AuditRequest):
    """Stub audit log (MVP)."""
    logger.info("AUDIT %s %s/%s", req.action, req.entity_type, req.entity_id)
    return {"ok": True}
