FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY auth/ ./auth/

EXPOSE 8006

CMD ["uvicorn", "auth.app:app", "--host", "0.0.0.0", "--port", "8006"]
