"""DTO для задач ИИ-генерации контент-плана (mk_plan_jobs).

ТЗ п.1, п.5: постановка задачи с указанием периода, направления,
целевой аудитории, целей публикаций и tone of voice.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class PlanJobCreate(BaseModel):
    period_start: date = Field(..., description="Начало периода контент-плана")
    period_end: date = Field(..., description="Конец периода контент-плана")
    direction_id: Optional[int] = Field(None, description="Направление бизнеса")
    audience: Optional[str] = Field(None, description="Описание целевой аудитории")
    goals: Optional[str] = Field(None, description="Цели публикаций (имиджевые/информационные/рекламные)")
    tone: Optional[str] = Field(None, description="Tone of voice / стиль")


class PlanJobRead(BaseModel):
    job_id: int
    period_start: date
    period_end: date
    direction_id: Optional[int] = None
    audience: Optional[str] = None
    goals: Optional[str] = None
    tone: Optional[str] = None
    status: str   # pending / running / done / failed
    created_by: Optional[int] = None
