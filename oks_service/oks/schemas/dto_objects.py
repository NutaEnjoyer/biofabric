from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class OksObjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    status_code: str = "planned"
    parent_object_id: Optional[int] = None
    initiator_user_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    department_id: Optional[int] = None
    object_type: Optional[str] = None
    description: Optional[str] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    external_object_id: Optional[str] = None


class OksObjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    status_code: Optional[str] = None
    parent_object_id: Optional[int] = None
    initiator_user_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    department_id: Optional[int] = None
    object_type: Optional[str] = None
    description: Optional[str] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    external_object_id: Optional[str] = None


class OksObjectOut(BaseModel):
    object_id: int
    code: Optional[str] = None
    name: str
    status_code: str
    parent_object_id: Optional[int] = None
    initiator_user_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    department_id: Optional[int] = None
    object_type: Optional[str] = None
    description: Optional[str] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    external_object_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children_count: int = 0
    stages_count: int = 0

    class Config:
        from_attributes = True
