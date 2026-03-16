from datetime import date
from typing import List
from ..common.errors import ValidationError
from ..repositories.ops_repo import create_operation


def _is_open_period(period_month: str) -> bool:
    """
    Период считается открытым, если он не старше предыдущего закрытого.
    Простое правило: нельзя вводить данные за период,
    который на 2+ месяца раньше текущей даты.
    Корректировки закрытых периодов — отдельный op_type 'adjustment'.
    """
    today = date.today()
    current_ym = today.strftime("%Y-%m")
    # разрешаем текущий и прошлый месяц как открытые
    if today.month == 1:
        prev_ym = f"{today.year - 1}-12"
    else:
        prev_ym = f"{today.year}-{today.month - 1:02d}"
    return period_month >= prev_ym


def create_operation_service(payload: dict, user: str) -> List[int]:
    op_type = payload.get("op_type")
    # для корректировки период закрытости не проверяем — это и есть механизм правки прошлых периодов
    if op_type != "adjustment" and not _is_open_period(payload["period_month"]):
        raise ValidationError(
            "Период закрыт: используйте корректировку (op_type=adjustment) для изменения данных прошлых периодов"
        )
    ids = create_operation(payload, created_by=user)
    return ids
