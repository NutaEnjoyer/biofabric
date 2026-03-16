"""Логирование (структурированное).

Что делает:
- Даёт функцию `log_event` для записи обозримых событий в STDOUT.
- На проде можно подключить JSON-логгер и трассировку.
"""
from datetime import datetime
from typing import Any

def log_event(event: str, **fields: Any) -> None:
    payload = {"ts": datetime.utcnow().isoformat()+"Z", "event": event, **fields}
    print(payload)  # для простоты; в реале лучше использовать стандартный логгер
