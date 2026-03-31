"""Auth Service — аутентификация и управление пользователями BioFabric ERP."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row

from auth.api.router import router
from auth.api.router_admin import router as admin_router
from auth.db import get_conn
from auth.security import hash_password
from auth.config import ADMIN_PASSWORD

app = FastAPI(
    title="Auth Service (BioFabric ERP)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/v1/auth")
app.include_router(admin_router, prefix="/v1/auth")


@app.on_event("startup")
def seed_admin():
    """При первом запуске создаёт пользователя admin@biofabric.ru со всеми ролями."""
    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT user_id FROM app_users WHERE email = 'admin@biofabric.ru' LIMIT 1"
                )
                if cur.fetchone():
                    return  # уже создан

                hashed = hash_password(ADMIN_PASSWORD)
                cur.execute(
                    """
                    INSERT INTO app_users (full_name, email, username, password_hash)
                    VALUES ('Администратор', 'admin@biofabric.ru', 'admin', %s)
                    ON CONFLICT DO NOTHING
                    RETURNING user_id
                    """,
                    [hashed],
                )
                row = cur.fetchone()
                if not row:
                    # Уже вставлен другим процессом
                    cur.execute(
                        "SELECT user_id FROM app_users WHERE email = 'admin@biofabric.ru'"
                    )
                    row = cur.fetchone()

                user_id = row["user_id"]

                # Назначить все существующие роли
                cur.execute("SELECT role_id FROM roles")
                for r in cur.fetchall():
                    cur.execute(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)"
                        " ON CONFLICT DO NOTHING",
                        [user_id, r["role_id"]],
                    )

        print(f"[auth] Admin user created: admin@biofabric.ru / {ADMIN_PASSWORD}")
    except Exception as e:
        print(f"[auth] Warning: could not seed admin user: {e}")


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}
