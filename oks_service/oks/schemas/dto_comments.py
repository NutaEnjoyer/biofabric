from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class OksCommentCreate(BaseModel):
    text: str
    stage_id: Optional[int] = None


class OksCommentOut(BaseModel):
    comment_id: int
    object_id: Optional[int] = None
    stage_id: Optional[int] = None
    author_id: Optional[int] = None
    text: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
