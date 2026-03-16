from pydantic import BaseModel, Field
from typing import Optional

class ApiResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None

class IdResponse(ApiResponse):
    id: int = Field(..., description="Идентификатор созданной сущности")
