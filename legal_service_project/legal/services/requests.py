"""
Legal Service — Service Layer
Бизнес-логика модуля юристов.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from psycopg import Connection

from legal.repositories.requests_repo import RequestsRepo


class RequestsService:
    """Сервис для работы с договорами и связанными операциями."""

    def __init__(self, conn: Connection):
        self.conn = conn
        self.repo = RequestsRepo(conn)

    # =========================================================================
    # 1) Привязка договора к workflow
    # =========================================================================
    def bind_workflow(self, contract_id: int) -> Dict[str, Any]:
        """
        Привязать договор к маршруту согласования.

        TЗ:
        - Привязать договор к активной дефиниции workflow 'contract_approval'.
        - Создать workflow_instance с entity_type='contract', state='draft'.
        - Если уже привязан — вернуть already_bound.

        Returns:
            {"wf_instance_id": int, "status": str}
        """
        wf_instance_id, status = self.repo.bind_workflow(contract_id)
        return {"wf_instance_id": wf_instance_id, "status": status}

    # =========================================================================
    # 2) Пометить просроченные договоры
    # =========================================================================
    def mark_overdue(self) -> Dict[str, Any]:
        """
        Пометить просроченные договоры статусом 'overdue'.

        TЗ:
        - Если end_date < now() и статус не completed/terminated/overdue,
          присвоить status_code='overdue'.
        - Запуск ручной (по кнопке/API).

        Returns:
            {"affected": int}
        """
        affected = self.repo.mark_overdue()
        return {"affected": affected}

    # =========================================================================
    # 3) KPI: доля договоров с гарантией
    # =========================================================================
    def guarantee_share(self) -> Dict[str, Any]:
        """
        Получить KPI: доля договоров с активной банковской гарантией.

        TЗ:
        - Среди всех contracts, у скольких есть bank_guarantees.status='active'.

        Returns:
            {"with_guarantee": int, "total": int, "pct": float}
        """
        return self.repo.get_guarantee_share()

    # =========================================================================
    # 4) Сводка нарушений и исключений
    # =========================================================================
    def issues(self, min_severity: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить сводку по рискам и отклонениям для всех договоров.

        TЗ:
        - Агрегировать contract_risks и contract_template_deviations.
        - Опциональный фильтр по severity >= min_severity.

        Returns:
            [{"contract_id": int, "risks_cnt": int, "deviations_cnt": int}, ...]
        """
        return self.repo.get_issues(min_severity)

    # =========================================================================
    # 5) Валидатор сторон договора
    # =========================================================================
    def validate_parties(self, contract_id: int) -> Dict[str, Any]:
        """
        Проверить корректность сторон договора.

        TЗ:
        - Роли только из набора: customer|supplier|guarantor|other.
        - Обязательно наличие customer и supplier.

        Returns:
            {"issues": [...]}
        """
        issues = self.repo.validate_parties(contract_id)
        return {"issues": issues}

    # =========================================================================
    # 6) Реестр договоров без гарантии
    # =========================================================================
    def without_guarantee(self) -> List[Dict[str, Any]]:
        """
        Получить список договоров без активной банковской гарантии.

        TЗ:
        - NOT EXISTS подзапрос к bank_guarantees.

        Returns:
            [{"contract_id": int, "contract_no": str, "title": str}, ...]
        """
        return self.repo.list_without_active_guarantee()

    # =========================================================================
    # 7) Уведомления по шаблону
    # =========================================================================
    def send_template(
        self,
        template_code: str,
        to: List[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Отправить уведомление через шаблон (outbox).

        TЗ:
        - Писать в notifications_outbox: template_code, to_json, payload_json, status='pending'.
        - Воркер ядра отправит (email/telegram).

        Returns:
            {"outbox_id": int}
        """
        outbox_id = self.repo.send_notification_template(template_code, to, payload)
        return {"outbox_id": outbox_id}

    # =========================================================================
    # 8) ЕИС: постановка в очередь
    # =========================================================================
    def eis_enqueue(
        self,
        contract_id: int,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Поставить договор в очередь экспорта в ЕИС.

        TЗ:
        - Создать запись в eis_export_queue(status='pending').
        - Создать jobs(type='send_eis_contract').
        - Ошибки фатальные, автоповторов нет.

        Returns:
            {"queue_id": int, "job_id": str}
        """
        queue_id, job_id = self.repo.enqueue_eis(contract_id, payload)
        return {"queue_id": queue_id, "job_id": job_id}

    # =========================================================================
    # 9a) Импорт из 1С: стейджинг
    # =========================================================================
    def import_1c_stage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сохранить входящий JSON из 1С в staging.

        TЗ:
        - Сохранить payload_json в import_contracts_1c.

        Returns:
            {"stage_id": int}
        """
        stage_id = self.repo.stage_1c(payload)
        return {"stage_id": stage_id}

    # =========================================================================
    # 9b) Импорт из 1С: upsert
    # =========================================================================
    def import_1c_upsert(self, stage_id: int) -> Dict[str, Any]:
        """
        Создать/обновить договор из staging-записи.

        TЗ:
        - По stage_id получить payload.
        - Upsert договора по ключу contract_no.
        - Устанавливает source_code = '1c_import'.

        Returns:
            {"contract_id": int}
        """
        contract_id = self.repo.upsert_contract_from_1c(stage_id)
        return {"contract_id": contract_id}

    # =========================================================================
    # 10) Синхронизация дедлайнов
    # =========================================================================
    def sync_deadlines(self, contract_id: int) -> Dict[str, Any]:
        """
        Пересоздать дедлайны для договора.

        TЗ:
        - Удалить старые дедлайны.
        - Создать новые по performance_due, payment_due, end_date.

        Returns:
            {"created": int}
        """
        created = self.repo.sync_deadlines_for_contract(contract_id)
        return {"created": created}

    # =========================================================================
    # CRUD операции
    # =========================================================================
    def get_contract(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """Получить договор по ID (с расширенными данными: риски, интеграция, ЕИС)."""
        return self.repo.get_contract(contract_id)

    def list_contracts(
        self,
        status_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получить список договоров (с индикаторами для реестра)."""
        return self.repo.list_contracts(status_code, limit, offset)

    # =========================================================================
    # 11) Таймлайн (история изменений)
    # =========================================================================
    def get_timeline(self, contract_id: int) -> List[Dict[str, Any]]:
        """
        Получить таймлайн (историю изменений) договора.

        TЗ:
        - Визуальная лента событий из contract_history.
        - Включает смену статусов, изменения параметров, действия пользователя.

        Returns:
            [{"history_id", "field_name", "old_value", "new_value",
              "changed_by", "changed_at", "reason"}, ...]
        """
        return self.repo.get_timeline(contract_id)

    # =========================================================================
    # 12) ИИ-анализ: получение
    # =========================================================================
    def get_ai_analysis(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить последний результат ИИ-анализа договора.

        TЗ:
        - Статус: Не выполнялся / Выполняется / Выполнен / Требует повторного анализа.
        - Показывает краткий итог и список выявленных элементов.
        - ИИ не принимает решений, не меняет статус договора.

        Returns:
            dict или None
        """
        return self.repo.get_latest_analysis(contract_id)

    # =========================================================================
    # 13) ИИ-анализ: запуск
    # =========================================================================
    def start_ai_analysis(
        self,
        contract_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Запустить ИИ-анализ договора.

        TЗ:
        - Запускается вручную по кнопке или автоматически при загрузке.
        - Один раз на версию документа.
        - Результаты носят рекомендательный характер.
        - Логирует: дату, пользователя, статус выполнения.

        Returns:
            {"analysis_id": int, "status": str}
        """
        return self.repo.start_analysis(contract_id, user_id)

    # =========================================================================
    # 14) Отправка договора в 1С (исходящая)
    # =========================================================================
    def send_to_1c(self, contract_id: int) -> Dict[str, Any]:
        """
        Поставить договор в очередь исходящей отправки в 1С.

        TЗ:
        - Кнопка «Отправить в 1С» доступна после согласования.
        - Отправка идемпотентна (повторный вызов не создаёт дубликат).
        - Ошибка интеграции не меняет бизнес-статус договора.
        - Статусы: not_sent → queued → sent | error.

        Returns:
            {"status": str, "job_id": str | None, "message": str | None}
        """
        return self.repo.send_to_1c(contract_id)
