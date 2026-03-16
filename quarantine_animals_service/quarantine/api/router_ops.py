from fastapi import APIRouter, Depends, Query
from ..schemas.dto_ops import OperationCreate
from ..schemas.dto_common import IdResponse, ApiResponse
from ..services.ops_service import create_operation_service
from ..repositories.ops_repo import confirm_operation, archive_operation, archive_month
from ..core_client import client as core
from .deps import get_current_user

router = APIRouter()

@router.post("/operations", response_model=IdResponse, summary="Создать операцию учета")
def create_operation_api(body: OperationCreate, user: str = Depends(get_current_user)):
    """
    Создает операцию в статусе 'in_process' (В обработке).
    Для `movement` достаточно одной записи с указанием источника/приемника — система создаст пару out/in.
    После сохранения отправляет уведомление через Core Service.
    """
    ids = create_operation_service(body.model_dump(), user=user)
    # Уведомление: перемещение или обычная операция
    if body.op_type == "movement" and len(ids) == 2:
        core.notify_movement(entry_out_id=ids[0], entry_in_id=ids[1])
    else:
        core.notify_operation_saved(entry_ids=ids, op_type=body.op_type)
    return IdResponse(ok=True, id=ids[0], message=f"Создано {len(ids)} запись(и)")


@router.patch("/operations/{entry_id}/confirm", response_model=ApiResponse, summary="Подтвердить запись (руководитель)")
def confirm_operation_api(entry_id: int, user: str = Depends(get_current_user)):
    """
    Переводит запись из статуса 'in_process' (В обработке) в 'current' (Актуальная).
    Выполняется руководителем участка.
    """
    confirm_operation(entry_id, approved_by=user)
    core.audit_log("qa_ledger", str(entry_id), "confirm", {"approved_by": user})
    return ApiResponse(ok=True, message="Запись подтверждена")


@router.patch("/operations/{entry_id}/archive", response_model=ApiResponse, summary="Архивировать запись")
def archive_operation_api(entry_id: int, user: str = Depends(get_current_user)):
    """
    Переводит запись из статуса 'current' (Актуальная) в 'archived' (Архивная).

    Архивная запись:
    - не редактируется;
    - участвует в агрегатах всех отчётов;
    - является неизменяемой историей учёта.

    Используется при закрытии периода.
    """
    archive_operation(entry_id, archived_by=user)
    return ApiResponse(ok=True, message="Запись архивирована")


@router.post("/operations/archive-month", response_model=ApiResponse, summary="Массовая архивация за месяц")
def archive_month_api(
    period_month: str = Query(..., description="Период YYYY-MM для архивации"),
    user: str = Depends(get_current_user),
):
    """
    Архивирует все 'current'-записи за указанный месяц одним действием.

    Используется при закрытии отчётного периода руководителем.
    Возвращает количество заархивированных записей.
    """
    count = archive_month(period_month, archived_by=user)
    return ApiResponse(ok=True, message=f"Архивировано записей: {count}")
