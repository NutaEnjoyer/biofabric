import uuid
from fastapi import Request

CORRELATION_HEADER = "X-Correlation-Id"

async def get_correlation_id(request: Request) -> str:
    cid = request.headers.get(CORRELATION_HEADER)
    return cid or str(uuid.uuid4())
