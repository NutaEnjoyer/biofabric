"""Роутер: аутентификация (login / me)."""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from psycopg.rows import dict_row

from auth.db import get_conn
from auth.security import verify_password, create_token, decode_token

router = APIRouter(tags=["Auth"])


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn):
    """Вход по email + пароль. Возвращает JWT и данные пользователя."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.email, u.password_hash,
                       ARRAY_AGG(r.role_code ORDER BY r.role_code)
                           FILTER (WHERE r.role_code IS NOT NULL) AS roles
                FROM app_users u
                LEFT JOIN user_roles ur ON ur.user_id = u.user_id
                LEFT JOIN roles r ON r.role_id = ur.role_id
                WHERE u.email = %s
                GROUP BY u.user_id
                """,
                [body.email],
            )
            user = cur.fetchone()

    if not user or not user.get("password_hash"):
        raise HTTPException(401, "Неверные учётные данные")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Неверные учётные данные")

    roles = user["roles"] or []
    token = create_token(user["user_id"], roles, user["full_name"], user["email"])
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "roles": roles,
        },
    }


def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Зависимость: декодирует Bearer-токен из заголовка Authorization."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")
    token = authorization[7:]
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(401, "Недействительный или просроченный токен")


@router.get("/me")
def me(user=Depends(get_current_user)):
    """Данные текущего пользователя из токена."""
    return {
        "user_id": user["sub"],
        "full_name": user.get("name"),
        "email": user.get("email"),
        "roles": user.get("roles", []),
    }
