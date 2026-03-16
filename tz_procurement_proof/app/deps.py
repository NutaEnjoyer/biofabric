from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import SessionLocal
from app.models import RoleEnum


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CurrentUser:
    """Текущий пользователь из заголовков запроса.

    Заголовки выставляются API-шлюзом после аутентификации:
      X-User-Id:    числовой ID из таблицы users
      X-User-Role:  одна из ролей RoleEnum (Инициатор, Директор, ...)

    При отсутствии заголовков — гость без прав (id=0, role=None).
    """
    def __init__(self, user_id: int, role: Optional[str]) -> None:
        self.user_id = user_id
        self.role = role

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    def require_role(self, *roles: str) -> None:
        if not self.has_role(*roles):
            raise HTTPException(
                status_code=403,
                detail=f"Требуется одна из ролей: {', '.join(roles)}. Текущая роль: {self.role or 'нет'}",
            )


def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> CurrentUser:
    """Извлечь текущего пользователя из HTTP-заголовков."""
    user_id = int(x_user_id) if x_user_id and x_user_id.isdigit() else 0
    return CurrentUser(user_id=user_id, role=x_user_role)
