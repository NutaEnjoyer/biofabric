from pydantic import BaseModel, Field
from typing import Optional, Any

class ResponseOk(BaseModel):
    ok: bool = True
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    ok: bool = False
    error: str = Field(..., description="Сообщение об ошибке")
