from contextlib import asynccontextmanager
from fastapi import Depends, Header
from ..common.correlation import get_correlation_id

@asynccontextmanager
async def lifespan(app):
    yield

def get_current_user(x_user_id: str | None = Header(default="system")) -> str:
    return x_user_id

async def get_correlation(cid: str = Depends(get_correlation_id)) -> str:
    return cid
