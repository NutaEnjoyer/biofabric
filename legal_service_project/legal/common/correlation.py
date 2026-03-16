import uuid

def new_correlation_id() -> str:
    return str(uuid.uuid4())
