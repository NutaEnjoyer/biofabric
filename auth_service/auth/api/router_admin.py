"""Роутер: администрирование пользователей и ролей."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from psycopg.rows import dict_row

from auth.db import get_conn
from auth.security import hash_password
from auth.api.router import get_current_user

router = APIRouter(tags=["Admin"])


def require_admin(user=Depends(get_current_user)):
    if "admin" not in (user.get("roles") or []):
        raise HTTPException(403, "Требуются права администратора")
    return user


# ─── Схемы ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    username: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class RolesSet(BaseModel):
    roles: list[str]  # список role_code


# ─── Пользователи ────────────────────────────────────────────────────────────

@router.get("/admin/users")
def list_users(_=Depends(require_admin)):
    """Список всех пользователей с их ролями."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT u.user_id, u.full_name, u.email, u.username, u.created_at,
                       ARRAY_AGG(r.role_code ORDER BY r.role_code)
                           FILTER (WHERE r.role_code IS NOT NULL) AS roles
                FROM app_users u
                LEFT JOIN user_roles ur ON ur.user_id = u.user_id
                LEFT JOIN roles r ON r.role_id = ur.role_id
                GROUP BY u.user_id
                ORDER BY u.created_at
            """)
            return cur.fetchall()


@router.post("/admin/users", status_code=201)
def create_user(body: UserCreate, _=Depends(require_admin)):
    """Создать нового пользователя."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO app_users (full_name, email, username, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id, full_name, email, username, created_at
                    """,
                    [body.full_name, body.email, body.username, hash_password(body.password)],
                )
                row = cur.fetchone()
            except Exception as e:
                raise HTTPException(409, f"Пользователь с таким email уже существует: {e}")
    return {**row, "roles": []}


@router.patch("/admin/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, _=Depends(require_admin)):
    """Обновить данные пользователя (имя, email, пароль)."""
    data = body.model_dump(exclude_none=True)
    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))
    if not data:
        raise HTTPException(400, "Нет данных для обновления")
    fields = list(data.keys())
    set_clause = ", ".join(f"{f} = %s" for f in fields)
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"UPDATE app_users SET {set_clause} WHERE user_id = %s"
                f" RETURNING user_id, full_name, email, username",
                [data[f] for f in fields] + [user_id],
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Пользователь не найден")
    return row


@router.delete("/admin/users/{user_id}", status_code=204)
def delete_user(user_id: int, current_user=Depends(require_admin)):
    """Удалить пользователя. Нельзя удалить себя."""
    if user_id == current_user["sub"]:
        raise HTTPException(400, "Нельзя удалить текущего пользователя")
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "DELETE FROM app_users WHERE user_id = %s RETURNING user_id", [user_id]
            )
            if not cur.fetchone():
                raise HTTPException(404, "Пользователь не найден")


# ─── Роли пользователя ───────────────────────────────────────────────────────

@router.put("/admin/users/{user_id}/roles")
def set_user_roles(user_id: int, body: RolesSet, _=Depends(require_admin)):
    """Заменить весь набор ролей пользователя."""
    with get_conn(autocommit=False) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT user_id FROM app_users WHERE user_id = %s", [user_id])
            if not cur.fetchone():
                conn.rollback()
                raise HTTPException(404, "Пользователь не найден")
            cur.execute("DELETE FROM user_roles WHERE user_id = %s", [user_id])
            for role_code in body.roles:
                cur.execute(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    SELECT %s, role_id FROM roles WHERE role_code = %s
                    ON CONFLICT DO NOTHING
                    """,
                    [user_id, role_code],
                )
        conn.commit()

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.email,
                       ARRAY_AGG(r.role_code ORDER BY r.role_code)
                           FILTER (WHERE r.role_code IS NOT NULL) AS roles
                FROM app_users u
                LEFT JOIN user_roles ur ON ur.user_id = u.user_id
                LEFT JOIN roles r ON r.role_id = ur.role_id
                WHERE u.user_id = %s
                GROUP BY u.user_id
                """,
                [user_id],
            )
            return cur.fetchone()


# ─── Справочник ролей ────────────────────────────────────────────────────────

@router.get("/admin/roles")
def list_roles(_=Depends(require_admin)):
    """Список всех доступных ролей."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT role_id, role_code, name FROM roles ORDER BY role_code")
            return cur.fetchall()
