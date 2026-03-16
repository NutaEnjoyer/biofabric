from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import metadata
from ..api.deps import get_db
from ..schemas.dto_sources import SourceCreate, SourceRead, FetchMaterialsRequest
from ..schemas.dto_common import ResponseOk
from ..repositories.sources_repo import SourcesRepo

router = APIRouter()

@router.post("/sources", response_model=ResponseOk)
async def add_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    """Добавить источник (TG/URL/RSS) в whitelist."""
    repo = SourcesRepo(metadata)
    sid = await repo.create(db, payload.name, payload.url, payload.kind or None)
    return ResponseOk(data={"source_id": sid})

@router.get("/sources", response_model=ResponseOk)
async def list_sources(db: AsyncSession = Depends(get_db)):
    """Список источников."""
    repo = SourcesRepo(metadata)
    rows = await repo.list(db)
    return ResponseOk(data=rows)

@router.delete("/sources/{source_id}", response_model=ResponseOk)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить источник из whitelist."""
    repo = SourcesRepo(metadata)
    await repo.delete(db, source_id)
    return ResponseOk()

@router.post("/sources/fetch", response_model=ResponseOk)
async def fetch_materials(req: FetchMaterialsRequest, db: AsyncSession = Depends(get_db)):
    """Забрать последние 10 материалов по каждому источнику (заглушка)."""
    repo = SourcesRepo(metadata)
    # Возвращаем пустой массив как заглушку (парсинг реализуется отдельно)
    res = {}
    return ResponseOk(data=res)
