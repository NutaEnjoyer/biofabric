"""
Legal Service — Dependencies
FastAPI зависимости для инъекции.
"""
from fastapi import Depends, Header, HTTPException
from typing import Optional
from legal.db import get_conn
from legal.services.requests import RequestsService
from legal.security.rbac import can as _can


class User:
    """Текущий пользователь (извлекается из заголовка X-User-Roles).

    В prod заменяется на реальную JWT-верификацию через Core.
    Заголовок X-User-Roles: legal_user,legal_admin (через запятую).
    Заголовок X-User-Id: числовой ID пользователя.
    """
    def __init__(self, user_id: int, roles: list[str]) -> None:
        self.user_id = user_id
        self.roles = roles


def get_db():
    """Получить соединение с БД."""
    with get_conn() as conn:
        yield conn


def get_service():
    """Получить экземпляр RequestsService с подключением к БД."""
    with get_conn(autocommit=False) as conn:
        yield RequestsService(conn)


def get_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_roles: Optional[str] = Header(None, alias="X-User-Roles"),
) -> User:
    """Получить текущего пользователя из заголовков запроса.

    Заголовки передаются API-шлюзом или фронтендом после аутентификации.
    При отсутствии заголовков возвращается гость без прав.
    """
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    roles = [r.strip() for r in x_user_roles.split(",")] if x_user_roles else []
    return User(user_id=user_id, roles=roles)


def require(action: str):
    """Dependency: проверить право на действие, иначе 403."""
    def _check(user: User = Depends(get_user)):
        if not _can(user, action):
            raise HTTPException(
                status_code=403,
                detail=f"Недостаточно прав для действия '{action}'"
            )
        return user
    return _check
