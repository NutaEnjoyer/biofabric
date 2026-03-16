
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models import StatusEnum, ApprovalDecisionEnum, OneCStatusEnum

class UserCreate(BaseModel):
    fio: str
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str

class UserOut(BaseModel):
    id: int
    fio: str
    role: str
    class Config:
        from_attributes = True

class RequestItemIn(BaseModel):
    nomenclature: str
    tech_spec: Optional[str] = None
    due_days: Optional[int] = None
    quantity: float
    justification: Optional[str] = None

class ProcurementCreate(BaseModel):
    subject: str = Field(..., description="Предмет закупки")
    justification: Optional[str] = None
    items: List[RequestItemIn]

class ProcurementOut(BaseModel):
    id: int
    subject: str
    justification: Optional[str]
    status: StatusEnum
    onec_status: OneCStatusEnum = OneCStatusEnum.not_sent
    class Config:
        from_attributes = True

class StatusPatch(BaseModel):
    status: StatusEnum

class ApprovalIn(BaseModel):
    request_id: int
    user_id: int
    decision: ApprovalDecisionEnum
    comment: Optional[str] = None

class SupplierQuoteIn(BaseModel):
    request_id: int
    supplier_name: str
    price: float
    delivery_days: Optional[int] = None
    payment_terms: Optional[str] = None
    comment: Optional[str] = None
    file_ref: Optional[str] = None

class SupplierQuoteOut(BaseModel):
    id: int
    request_id: int
    supplier_name: str
    price: float
    delivery_days: Optional[int]
    payment_terms: Optional[str]
    comment: Optional[str]
    file_ref: Optional[str]
    is_selected: bool
    class Config:
        from_attributes = True

class DocumentIn(BaseModel):
    request_id: int
    doc_type: str
    filename: str
    storage_url: Optional[str] = None
    signed: bool = False
