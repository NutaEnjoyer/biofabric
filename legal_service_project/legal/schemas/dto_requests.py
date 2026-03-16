from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class BindWorkflowResponse(BaseModel):
    wf_instance_id: int
    status: str

class GuaranteeShare(BaseModel):
    with_guarantee: int
    total: int
    pct: float

class ContractIssueRow(BaseModel):
    contract_id: int
    risks_cnt: int
    deviations_cnt: int

class SendTemplateRequest(BaseModel):
    template_code: str
    to: List[str]
    payload: Dict[str, Any] = {}

class SendTemplateResponse(BaseModel):
    outbox_id: int

class EISEnqueueRequest(BaseModel):
    contract_id: int
    payload: Dict[str, Any] = {}

class EISEnqueueResponse(BaseModel):
    queue_id: int
    job_id: str

class Import1CStageRequest(BaseModel):
    payload: Dict[str, Any]

class Import1CStageResponse(BaseModel):
    stage_id: int

class Import1CUpsertResponse(BaseModel):
    contract_id: int

class ValidatePartiesResponse(BaseModel):
    issues: List[str]

class ContractShort(BaseModel):
    contract_id: int
    contract_no: str

# ─── Таймлайн ────────────────────────────────────────────────────────────────

class TimelineEntry(BaseModel):
    history_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[int] = None
    changed_at: str
    reason: Optional[str] = None

# ─── ИИ-анализ ───────────────────────────────────────────────────────────────

class AIAnalysis(BaseModel):
    analysis_id: int
    status: str  # pending | running | done | needs_rerun
    analyzed_by: Optional[int] = None
    analyzed_at: Optional[str] = None
    document_version: Optional[str] = None
    deviations_count: int = 0
    has_critical_risk: bool = False
    summary_text: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    analysis_id: int
    status: str

# ─── Отправка в 1С ───────────────────────────────────────────────────────────

class Send1CResponse(BaseModel):
    status: str
    job_id: Optional[str] = None
    message: Optional[str] = None
