from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class OksStageCreate(BaseModel):
    name: str
    parent_stage_id: Optional[int] = None
    status_code: str = "planned"
    stage_owner_user_id: Optional[int] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    suspend_reason_text: Optional[str] = None
    external_stage_id: Optional[str] = None


class OksStageUpdate(BaseModel):
    name: Optional[str] = None
    parent_stage_id: Optional[int] = None
    status_code: Optional[str] = None
    stage_owner_user_id: Optional[int] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    is_completed: Optional[bool] = None
    completed_at: Optional[date] = None
    has_issue: Optional[bool] = None
    suspend_reason_text: Optional[str] = None
    external_stage_id: Optional[str] = None


class OksStageOut(BaseModel):
    stage_id: int
    object_id: int
    parent_stage_id: Optional[int] = None
    name: str
    status_code: str
    stage_owner_user_id: Optional[int] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    is_completed: bool = False
    completed_at: Optional[date] = None
    has_issue: bool = False
    suspend_reason_text: Optional[str] = None
    external_stage_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_overdue: bool = False

    class Config:
        from_attributes = True
