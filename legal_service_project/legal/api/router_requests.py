"""
Legal Service — API Router
HTTP-эндпоинты модуля юристов.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from legal.api.deps import get_service, require
from legal.services.requests import RequestsService
from legal.schemas.dto_requests import (
    BindWorkflowResponse,
    GuaranteeShare,
    ContractIssueRow,
    SendTemplateRequest,
    SendTemplateResponse,
    EISEnqueueRequest,
    EISEnqueueResponse,
    Import1CStageRequest,
    Import1CStageResponse,
    Import1CUpsertResponse,
    ValidatePartiesResponse,
    ContractShort,
    TimelineEntry,
    AIAnalysis,
    StartAnalysisResponse,
    Send1CResponse,
)

router = APIRouter(tags=["legal-contracts"])


# =============================================================================
# Договоры: CRUD (статические роуты ПЕРЕД динамическими!)
# =============================================================================

@router.get("/contracts", summary="Список договоров")
def list_contracts(
    status_code: Optional[str] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> dict:
    """Получить список договоров с индикаторами (source, guarantee, deviations, overdue)."""
    items = service.list_contracts(status_code=status_code, limit=limit, offset=offset)
    return {"items": items, "count": len(items)}


@router.post("/contracts/mark-overdue", summary="Пометить просроченные договоры")
def mark_overdue(
    service: RequestsService = Depends(get_service),
    _user=Depends(require("mark_overdue")),
) -> dict:
    """
    Пометить статусом 'overdue' все договоры с истёкшим end_date.

    Возвращает количество затронутых записей.
    """
    result = service.mark_overdue()
    return {"affected": result["affected"]}


@router.get(
    "/contracts/without-guarantee",
    response_model=List[ContractShort],
    summary="Договоры без активной гарантии"
)
def without_guarantee(
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> List[ContractShort]:
    """Получить список договоров без активной банковской гарантии."""
    items = service.without_guarantee()
    return [ContractShort(contract_id=i["contract_id"], contract_no=i["contract_no"]) for i in items]


# Динамический роут ПОСЛЕ статических
@router.get("/contracts/{contract_id}", summary="Получить договор")
def get_contract(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> dict:
    """Получить договор по ID с расширенными данными: риски, интеграция, ЕИС-статус."""
    contract = service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    return contract


# =============================================================================
# 1) Привязка к workflow
# =============================================================================

@router.post(
    "/contracts/{contract_id}/workflow/bind",
    response_model=BindWorkflowResponse,
    summary="Привязать договор к workflow"
)
def bind_workflow(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("bind_workflow")),
) -> BindWorkflowResponse:
    """
    Привязать договор к маршруту согласования 'contract_approval'.

    - Если уже привязан — вернёт status='already_bound'.
    - Иначе создаст workflow_instance и вернёт status='bound'.
    """
    try:
        result = service.bind_workflow(contract_id)
        return BindWorkflowResponse(
            wf_instance_id=result["wf_instance_id"],
            status=result["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 2) KPI: доля с гарантией
# =============================================================================

@router.get(
    "/kpi/guarantee-share",
    response_model=GuaranteeShare,
    summary="KPI: доля договоров с гарантией"
)
def guarantee_share(
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> GuaranteeShare:
    """
    Получить долю договоров с активной банковской гарантией.

    - with_guarantee: количество договоров с активной гарантией
    - total: общее количество договоров
    - pct: процент (0-100)
    """
    result = service.guarantee_share()
    return GuaranteeShare(**result)


# =============================================================================
# 3) Сводка нарушений
# =============================================================================

@router.get(
    "/kpi/issues",
    response_model=List[ContractIssueRow],
    summary="Сводка рисков и отклонений"
)
def get_issues(
    min_severity: Optional[int] = Query(
        None, ge=1, le=5,
        description="Минимальный уровень severity для фильтрации рисков"
    ),
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> List[ContractIssueRow]:
    """
    Агрегированная сводка по рискам и отклонениям для всех договоров.

    - risks_cnt: количество нерешённых рисков
    - deviations_cnt: количество неутверждённых отклонений
    """
    items = service.issues(min_severity=min_severity)
    return [ContractIssueRow(**item) for item in items]


# =============================================================================
# 4) Валидация сторон
# =============================================================================

@router.get(
    "/contracts/{contract_id}/validate-parties",
    response_model=ValidatePartiesResponse,
    summary="Валидация сторон договора"
)
def validate_parties(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> ValidatePartiesResponse:
    """
    Проверить корректность сторон договора.

    Возможные проблемы:
    - contract_not_found — договор не найден
    - unsupported_role_in_contract_parties — неподдерживаемая роль
    - missing_customer — отсутствует заказчик
    - missing_supplier — отсутствует поставщик
    """
    result = service.validate_parties(contract_id)
    return ValidatePartiesResponse(issues=result["issues"])


# =============================================================================
# 5) Уведомления
# =============================================================================

@router.post(
    "/notifications/send",
    response_model=SendTemplateResponse,
    summary="Отправить уведомление по шаблону"
)
def send_notification(
    body: SendTemplateRequest,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("send_notification")),
) -> SendTemplateResponse:
    """
    Поставить уведомление в очередь отправки (outbox).

    Воркер ядра отправит сообщение по шаблону (email/telegram).
    """
    result = service.send_template(
        template_code=body.template_code,
        to=body.to,
        payload=body.payload
    )
    return SendTemplateResponse(outbox_id=result["outbox_id"])


# =============================================================================
# 6) ЕИС
# =============================================================================

@router.post(
    "/eis/enqueue",
    response_model=EISEnqueueResponse,
    summary="Поставить договор в очередь ЕИС"
)
def eis_enqueue(
    body: EISEnqueueRequest,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("send_to_eis")),
) -> EISEnqueueResponse:
    """
    Поставить договор в очередь экспорта в ЕИС.

    - Создаёт запись в eis_export_queue.
    - Создаёт job для фоновой отправки.
    - Ошибки фатальные, автоповторов нет.
    """
    try:
        result = service.eis_enqueue(
            contract_id=body.contract_id,
            payload=body.payload
        )
        return EISEnqueueResponse(
            queue_id=result["queue_id"],
            job_id=result["job_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 7) Импорт из 1С
# =============================================================================

@router.post(
    "/import/1c/stage",
    response_model=Import1CStageResponse,
    summary="Импорт из 1С: сохранить в staging"
)
def import_1c_stage(
    body: Import1CStageRequest,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("import_1c")),
) -> Import1CStageResponse:
    """
    Сохранить входящий JSON из 1С в staging-таблицу.

    Затем вызвать /import/1c/upsert/{stage_id} для создания/обновления договора.
    """
    result = service.import_1c_stage(body.payload)
    return Import1CStageResponse(stage_id=result["stage_id"])


@router.post(
    "/import/1c/upsert/{stage_id}",
    response_model=Import1CUpsertResponse,
    summary="Импорт из 1С: создать/обновить договор"
)
def import_1c_upsert(
    stage_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("import_1c")),
) -> Import1CUpsertResponse:
    """
    Создать или обновить договор из staging-записи.
    Устанавливает source_code='1c_import'.

    Обязательное поле в payload: contract_no.
    """
    try:
        result = service.import_1c_upsert(stage_id)
        return Import1CUpsertResponse(contract_id=result["contract_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 8) Синхронизация дедлайнов
# =============================================================================

@router.post(
    "/contracts/{contract_id}/sync-deadlines",
    summary="Синхронизировать дедлайны договора"
)
def sync_deadlines(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("sync_deadlines")),
) -> dict:
    """
    Пересоздать дедлайны для договора на основе его дат.

    Удаляет старые и создаёт новые по:
    - performance_due → contract_execution_due
    - payment_due → contract_payment_due
    - end_date → contract_end
    """
    try:
        result = service.sync_deadlines(contract_id)
        return {"created": result["created"]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# 9) Таймлайн договора
# =============================================================================

@router.get(
    "/contracts/{contract_id}/timeline",
    response_model=List[TimelineEntry],
    summary="История изменений договора"
)
def get_timeline(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> List[TimelineEntry]:
    """
    Получить таймлайн (историю изменений) договора.

    Отражает: создание, изменения параметров, смену статусов,
    отправку в ЕИС, ручные действия пользователя.
    """
    entries = service.get_timeline(contract_id)
    return [TimelineEntry(**e) for e in entries]


# =============================================================================
# 10) ИИ-анализ договора
# =============================================================================

@router.get(
    "/contracts/{contract_id}/ai-analysis",
    summary="Получить результат ИИ-анализа"
)
def get_ai_analysis(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("view_contract")),
) -> dict:
    """
    Получить последний результат ИИ-анализа договора.

    Статусы: pending | running | done | needs_rerun.
    Результаты носят рекомендательный характер.
    """
    result = service.get_ai_analysis(contract_id)
    if result is None:
        return {"status": "not_started"}
    return result


@router.post(
    "/contracts/{contract_id}/ai-analysis/start",
    response_model=StartAnalysisResponse,
    summary="Запустить ИИ-анализ договора"
)
def start_ai_analysis(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("start_ai_analysis")),
) -> StartAnalysisResponse:
    """
    Запустить ИИ-анализ договора.

    - Анализирует отклонения от шаблона и критические риски.
    - Формирует резюме на основе данных договора.
    - Логирует: дату, пользователя, статус выполнения.
    - Результаты не изменяют статус договора автоматически.
    """
    try:
        result = service.start_ai_analysis(contract_id)
        return StartAnalysisResponse(
            analysis_id=result["analysis_id"],
            status=result["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# 11) Отправка договора в 1С (исходящая интеграция)
# =============================================================================

@router.post(
    "/contracts/{contract_id}/send-to-1c",
    response_model=Send1CResponse,
    summary="Отправить договор в 1С"
)
def send_to_1c(
    contract_id: int,
    service: RequestsService = Depends(get_service),
    _user=Depends(require("send_to_1c")),
) -> Send1CResponse:
    """
    Поставить договор в очередь исходящей отправки в 1С.

    - Действие идемпотентно (повторный вызов не создаёт дубликат).
    - Ошибка интеграции не блокирует работу юриста.
    - Статус интеграции независим от бизнес-статуса договора.
    - Статусы: not_sent → queued → sent | error.
    """
    try:
        result = service.send_to_1c(contract_id)
        return Send1CResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
