from fastapi import APIRouter, Response, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.db import get_db
from core.config import settings
from core.auth.jwt_utils import sign_jwt

router = APIRouter()

class LoginIn(BaseModel):
    email: str
    password: str
    as_cookie: bool = True

@router.post("/auth/login")
def login(body: LoginIn, response: Response, db = Depends(get_db)):
    # Используем app_users: user_id BIGINT, email TEXT
    row = db.execute(text("SELECT user_id, email FROM app_users WHERE email=:e LIMIT 1"), {"e": body.email}).mappings().first()
    if not row:
        return {"ok": False, "error": "Неверные учётные данные"}
    user_id = int(row["user_id"])
    access = sign_jwt({"sub": user_id}, settings.JWT_ACCESS_SECRET, ttl_minutes=20)
    refresh = sign_jwt({"sub": user_id}, settings.JWT_REFRESH_SECRET, ttl_minutes=60*24*14)
    if body.as_cookie:
        response.set_cookie("access_token", access, httponly=True, secure=True, samesite="lax", max_age=20*60)
        response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="lax", max_age=60*60*24*14)
        return {"ok": True, "mode": "cookie"}
    return {"access": access, "refresh": refresh, "mode": "header"}

@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}
