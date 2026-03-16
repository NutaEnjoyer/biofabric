from pydantic import BaseModel
from typing import Optional, List

class PlanFromPromptRequest(BaseModel):
    prompt: str
    channels: Optional[List[int]] = None
    formats: Optional[List[int]] = None

class PlanFromPromptResult(BaseModel):
    created_post_ids: List[int]

class IdeasFromSourcesRequest(BaseModel):
    source_ids: Optional[List[int]] = None  # если None — взять все
    limit_per_source: int = 10

class IdeasFromSourcesResult(BaseModel):
    created_post_ids: List[int]  # посты-идеи без даты (draft)
