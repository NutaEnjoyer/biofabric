import csv
from io import StringIO
from fastapi import APIRouter, UploadFile, File, Depends
from ..schemas.dto_common import ApiResponse
from ..services.ops_service import create_operation_service
from ..common.errors import ValidationError
from ..core_client import client as core
from .deps import get_current_user

router = APIRouter()
REQUIRED_COLS = ["date","period_month","op_type","species_code","direction_code","quantity"]

@router.post("/import", response_model=ApiResponse, summary="Импорт CSV с операциями")
async def import_csv(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    if not file.filename.endswith(".csv"):
        raise ValidationError("Ожидается CSV (Excel сохраните как CSV UTF-8)")
    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    for col in REQUIRED_COLS:
        if col not in reader.fieldnames:
            raise ValidationError(f"Нет обязательной колонки: {col}")
    created = 0
    for i, row in enumerate(reader, start=2):
        try:
            row["quantity"] = int(row["quantity"])
            create_operation_service(row, user=user)
            created += 1
        except Exception as e:
            err_msg = f"Строка {i}: {e}"
            core.notify_validation_error(err_msg)
            raise ValidationError(err_msg)
    core.notify_operation_saved(entry_ids=[], op_type=f"csv_import ({created} rows)")
    return ApiResponse(ok=True, message=f"Импорт завершен. Создано: {created}")
