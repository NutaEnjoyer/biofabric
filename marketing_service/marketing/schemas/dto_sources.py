from pydantic import BaseModel
from typing import Optional, Literal, List

SourceKind = Literal["tg", "url", "rss"]

class SourceCreate(BaseModel):
    name: str
    url: str
    kind: Optional[SourceKind] = None

class SourceRead(BaseModel):
    source_id: int
    name: str
    url: str
    kind: Optional[SourceKind] = None
    approved: bool

class FetchMaterialsRequest(BaseModel):
    source_ids: Optional[List[int]] = None
