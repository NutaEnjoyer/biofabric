from fastapi import Depends, Header, HTTPException
from typing import Optional
from oks.db import get_conn
from oks.security.rbac import can as _can


class User:
    """Текущий пользователь из заголовков X-User-Id / X-User-Roles."""

    def __init__(self, user_id: int, roles: list[str]) -> None:
        self.user_id = user_id
        self.roles = roles


def get_db():
    with get_conn() as conn:
        yield conn


def get_db_tx():
    with get_conn(autocommit=False) as conn:
        yield conn


def get_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_roles: Optional[str] = Header(None, alias="X-User-Roles"),
) -> User:
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    roles = [r.strip() for r in x_user_roles.split(",")] if x_user_roles else []
    return User(user_id=user_id, roles=roles)


def require(action: str):
    def _check(user: User = Depends(get_user)):
        if not _can(user, action):
            raise HTTPException(
                status_code=403,
                detail=f"Недостаточно прав для действия '{action}'",
            )
        return user
    return _check
