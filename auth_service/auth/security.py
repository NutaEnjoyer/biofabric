from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt

from auth.config import JWT_SECRET, JWT_ALGORITHM, JWT_TTL_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_token(user_id: int, roles: list[str], full_name: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "name": full_name,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
