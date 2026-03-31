from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


DOC_TYPES = {"order", "memo", "act", "spec", "drawing", "tz", "contract", "scan_archive", "other"}
DOC_STATUSES = {"draft", "review", "approved"}


class OksDocCreate(BaseModel):
    title: str
    file_path: Optional[str] = None
    doc_type: str = "other"
    doc_status: str = "draft"
    bind_object_type: str = "object"
    bind_object_id: Optional[int] = None
    description: Optional[str] = None
    mime_type: Optional[str] = None


class OksDocUpdate(BaseModel):
    doc_status: Optional[str] = None
    doc_type: Optional[str] = None


class OksDocOut(BaseModel):
    oks_doc_id: int
    document_id: int
    title: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    doc_type: str
    doc_status: str
    bind_object_type: str
    bind_object_id: int
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
