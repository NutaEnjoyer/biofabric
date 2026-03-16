from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db

router = APIRouter()

class CommentIn(BaseModel):
    entity_type: str
    entity_id: str
    body: str

@router.post("/comments")
def create_comment(body: CommentIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO comments(entity_type, entity_id, author_user_id, body, created_at) VALUES (:t,:i,NULL,:b,NOW())"),
               {"t": body.entity_type, "i": body.entity_id, "b": body.body})
    db.commit()
    return {"ok": True}

class TagIn(BaseModel):
    entity_type: str
    entity_id: str
    tag: str

@router.post("/tags")
def add_tag(body: TagIn, db = Depends(get_db)):
    db.execute(text("INSERT INTO entity_tags(entity_type, entity_id, tag, created_at) VALUES (:t,:i,:g,NOW())"),
               {"t": body.entity_type, "i": body.entity_id, "g": body.tag})
    db.commit()
    return {"ok": True}
