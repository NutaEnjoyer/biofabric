import os

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://biofabric:biofabric_secret@localhost:5432/biofabric",
)

JWT_SECRET: str = os.environ.get("JWT_SECRET", "biofabric-jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_TTL_MINUTES = 480  # 8 часов

# Пароль администратора по умолчанию при первом запуске
ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin123")
