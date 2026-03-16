FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем pyproject.toml и устанавливаем зависимости
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Копируем код приложения
COPY legal/ ./legal/

# Порт
EXPOSE 8001

# Запуск
CMD ["uvicorn", "legal.app:app", "--host", "0.0.0.0", "--port", "8001"]
