FROM python:3.11-slim

WORKDIR /app

# Зависимости системы (gcc + libpq нужны для asyncpg и psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Копируем код сервиса
COPY marketing/ ./marketing/

EXPOSE 8002

CMD ["uvicorn", "marketing.app:app", "--host", "0.0.0.0", "--port", "8002"]
