"""
Legal Service — Repository Layer
SQL-операции для модуля юристов.
"""
from __future__ import annotations
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from psycopg import Connection

ALLOWED_PARTY_ROLES = {"customer", "supplier", "guarantor", "other"}


class RequestsRepo:
    """Репозиторий для работы с договорами и связанными сущностями."""

    def __init__(self, conn: Connection):
        self.conn = conn

    # =========================================================================
    # 1) Привязка договора к workflow
    # =========================================================================
    def bind_workflow(self, contract_id: int) -> Tuple[int, str]:
        """
        Привязать договор к активному workflow 'contract_approval'.

        Returns:
            (wf_instance_id, status) где status = 'bound' | 'already_bound'
        """
        cur = self.conn.cursor()

        # Проверяем существование договора
        cur.execute("SELECT 1 FROM contracts WHERE contract_id = %s", (contract_id,))
        if not cur.fetchone():
            raise ValueError(f"Договор {contract_id} не найден")

        # Проверяем, есть ли уже привязка
        cur.execute(
            "SELECT wf_instance_id FROM contract_workflow_bind WHERE contract_id = %s",
            (contract_id,)
        )
        row = cur.fetchone()
        if row:
            return (row[0], "already_bound")

        # Ищем активную дефиницию workflow
        cur.execute("""
            SELECT id, config_json
            FROM workflow_definitions
            WHERE code = 'contract_approval' AND is_active = TRUE
            ORDER BY version DESC
            LIMIT 1
        """)
        wf_def = cur.fetchone()
        if not wf_def:
            raise ValueError("Workflow 'contract_approval' не найден или не активен")

        def_id, config_json = wf_def
        config = json.loads(config_json) if isinstance(config_json, str) else config_json
        steps = config.get("steps", [])
        initial_state = steps[0] if steps else "draft"

        # Создаём instance
        cur.execute("""
            INSERT INTO workflow_instances(definition_id, entity_type, entity_id, state, context_json, created_at)
            VALUES (%s, 'contract', %s, %s, '{}'::jsonb, NOW())
            RETURNING id
        """, (def_id, str(contract_id), initial_state))
        wf_instance_id = cur.fetchone()[0]

        # Привязываем к договору
        cur.execute("""
            INSERT INTO contract_workflow_bind(contract_id, wf_instance_id, created_at)
            VALUES (%s, %s, NOW())
        """, (contract_id, wf_instance_id))

        self.conn.commit()
        return (wf_instance_id, "bound")

    # =========================================================================
    # 2) Пометить просроченные договоры
    # =========================================================================
    def mark_overdue(self) -> int:
        """
        Пометить статусом 'overdue' договоры с истёкшим end_date.

        Returns:
            Количество обновлённых записей
        """
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE contracts
            SET status_code = 'overdue', updated_at = NOW()
            WHERE end_date IS NOT NULL
              AND end_date < CURRENT_DATE
              AND status_code NOT IN ('completed', 'terminated', 'archived', 'overdue')
        """)
        affected = cur.rowcount
        self.conn.commit()
        return affected

    # =========================================================================
    # 3) KPI: доля договоров с активной гарантией
    # =========================================================================
    def get_guarantee_share(self) -> Dict[str, Any]:
        """
        Вычислить долю договоров с активной банковской гарантией.

        Returns:
            {"with_guarantee": int, "total": int, "pct": float}
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT
                COUNT(DISTINCT c.contract_id) FILTER (
                    WHERE EXISTS (
                        SELECT 1 FROM bank_guarantees bg
                        WHERE bg.contract_id = c.contract_id AND bg.status = 'active'
                    )
                ) AS with_guarantee,
                COUNT(DISTINCT c.contract_id) AS total
            FROM contracts c
        """)
        row = cur.fetchone()
        with_guarantee, total = row[0] or 0, row[1] or 0
        pct = round(100.0 * with_guarantee / total, 2) if total > 0 else 0.0
        return {"with_guarantee": with_guarantee, "total": total, "pct": pct}

    # =========================================================================
    # 4) Сводка нарушений и исключений
    # =========================================================================
    def get_issues(self, min_severity: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Агрегировать риски и отклонения по договорам.

        Args:
            min_severity: минимальный уровень severity для фильтрации рисков (1-5)

        Returns:
            [{"contract_id": int, "risks_cnt": int, "deviations_cnt": int}, ...]
        """
        cur = self.conn.cursor()

        severity_filter = ""
        params: List[Any] = []
        if min_severity is not None:
            severity_filter = "AND cr.severity >= %s"
            params.append(min_severity)

        query = f"""
            WITH risks AS (
                SELECT contract_id, COUNT(*) AS risks_cnt
                FROM contract_risks cr
                WHERE cr.resolved_at IS NULL {severity_filter}
                GROUP BY contract_id
            ),
            deviations AS (
                SELECT contract_id, COUNT(*) AS deviations_cnt
                FROM contract_template_deviations
                WHERE approved_at IS NULL
                GROUP BY contract_id
            )
            SELECT
                c.contract_id,
                COALESCE(r.risks_cnt, 0) AS risks_cnt,
                COALESCE(d.deviations_cnt, 0) AS deviations_cnt
            FROM contracts c
            LEFT JOIN risks r ON r.contract_id = c.contract_id
            LEFT JOIN deviations d ON d.contract_id = c.contract_id
            ORDER BY c.contract_id
        """
        cur.execute(query, params)
        return [
            {"contract_id": row[0], "risks_cnt": row[1], "deviations_cnt": row[2]}
            for row in cur.fetchall()
        ]

    # =========================================================================
    # 5) Валидатор сторон договора
    # =========================================================================
    def validate_parties(self, contract_id: int) -> List[str]:
        """
        Проверить корректность сторон договора.

        Returns:
            Список проблем: ["unsupported_role", "missing_customer", "missing_supplier"]
        """
        cur = self.conn.cursor()
        issues: List[str] = []

        # Проверяем существование договора
        cur.execute("SELECT 1 FROM contracts WHERE contract_id = %s", (contract_id,))
        if not cur.fetchone():
            return ["contract_not_found"]

        # Получаем все роли сторон
        cur.execute(
            "SELECT role_code FROM contract_parties WHERE contract_id = %s",
            (contract_id,)
        )
        roles = {row[0] for row in cur.fetchall()}

        # Проверяем неподдерживаемые роли
        unsupported = roles - ALLOWED_PARTY_ROLES
        if unsupported:
            issues.append("unsupported_role_in_contract_parties")

        # Проверяем обязательные роли
        if "customer" not in roles:
            issues.append("missing_customer")
        if "supplier" not in roles:
            issues.append("missing_supplier")

        return issues

    # =========================================================================
    # 6) Реестр договоров без активной гарантии
    # =========================================================================
    def list_without_active_guarantee(self) -> List[Dict[str, Any]]:
        """
        Получить список договоров без активной банковской гарантии.

        Returns:
            [{"contract_id": int, "contract_no": str}, ...]
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT c.contract_id, c.contract_no, c.title
            FROM contracts c
            WHERE NOT EXISTS (
                SELECT 1 FROM bank_guarantees bg
                WHERE bg.contract_id = c.contract_id AND bg.status = 'active'
            )
            ORDER BY c.contract_id
        """)
        return [
            {"contract_id": row[0], "contract_no": row[1], "title": row[2]}
            for row in cur.fetchall()
        ]

    # =========================================================================
    # 7) Уведомления (режим шаблонов)
    # =========================================================================
    def send_notification_template(
        self,
        template_code: str,
        to: List[str],
        payload: Dict[str, Any]
    ) -> int:
        """
        Поставить уведомление в очередь отправки (outbox).

        Returns:
            outbox_id
        """
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO notifications_outbox(
                template_code, to_json, payload_json, status, updated_at
            )
            VALUES (%s, %s, %s, 'pending', NOW())
            RETURNING outbox_id
        """, (template_code, json.dumps(to), json.dumps(payload)))
        outbox_id = cur.fetchone()[0]
        self.conn.commit()
        return outbox_id

    # =========================================================================
    # 8) ЕИС: постановка в очередь + создание job
    # =========================================================================
    def enqueue_eis(self, contract_id: int, payload: Dict[str, Any]) -> Tuple[int, str]:
        """
        Поставить договор в очередь экспорта в ЕИС и создать job.

        Returns:
            (queue_id, job_id)
        """
        cur = self.conn.cursor()

        # Проверяем существование договора
        cur.execute("SELECT 1 FROM contracts WHERE contract_id = %s", (contract_id,))
        if not cur.fetchone():
            raise ValueError(f"Договор {contract_id} не найден")

        # Создаём запись в очереди
        cur.execute("""
            INSERT INTO eis_export_queue(contract_id, payload_json, status, created_at, updated_at)
            VALUES (%s, %s, 'pending', NOW(), NOW())
            RETURNING queue_id
        """, (contract_id, json.dumps(payload)))
        queue_id = cur.fetchone()[0]

        # Создаём job
        job_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO jobs(id, type, payload_json, run_at, status, attempts, idempotency_key, created_at)
            VALUES (%s, 'send_eis_contract', %s, NOW(), 'pending', 0, %s, NOW())
        """, (job_id, json.dumps({"queue_id": queue_id}), f"eis:{queue_id}"))

        self.conn.commit()
        return (queue_id, job_id)

    # =========================================================================
    # 9a) Импорт из 1С: стейджинг
    # =========================================================================
    def stage_1c(self, payload: Dict[str, Any]) -> int:
        """
        Сохранить входящие данные из 1С в staging-таблицу.

        Returns:
            stage_id
        """
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO import_contracts_1c(payload_json, received_at)
            VALUES (%s, NOW())
            RETURNING id
        """, (json.dumps(payload),))
        stage_id = cur.fetchone()[0]
        self.conn.commit()
        return stage_id

    # =========================================================================
    # 9b) Импорт из 1С: upsert договора
    # =========================================================================
    def upsert_contract_from_1c(self, stage_id: int) -> int:
        """
        Создать или обновить договор из staging-записи.
        Устанавливает source_code = '1c_import'.

        Returns:
            contract_id
        """
        cur = self.conn.cursor()

        # Получаем данные из staging
        cur.execute(
            "SELECT payload_json FROM import_contracts_1c WHERE id = %s",
            (stage_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Staging-запись {stage_id} не найдена")

        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])

        # Обязательные поля
        contract_no = payload.get("contract_no")
        title = payload.get("title") or payload.get("name") or f"Договор {contract_no}"
        if not contract_no:
            raise ValueError("Отсутствует обязательное поле 'contract_no'")

        # Опциональные поля
        amount_total = payload.get("amount_total")
        currency = payload.get("currency", "RUB")
        status_code = payload.get("status_code", "draft")

        # Upsert с фиксацией источника
        cur.execute("""
            INSERT INTO contracts(
                contract_no, title, status_code, amount_total, currency,
                source_code, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, '1c_import', NOW(), NOW())
            ON CONFLICT (contract_no) DO UPDATE SET
                title = EXCLUDED.title,
                amount_total = COALESCE(EXCLUDED.amount_total, contracts.amount_total),
                currency = COALESCE(EXCLUDED.currency, contracts.currency),
                source_code = '1c_import',
                updated_at = NOW()
            RETURNING contract_id
        """, (contract_no, title, status_code, amount_total, currency))
        contract_id = cur.fetchone()[0]

        self.conn.commit()
        return contract_id

    # =========================================================================
    # 10) Синхронизация дедлайнов
    # =========================================================================
    def sync_deadlines_for_contract(self, contract_id: int) -> int:
        """
        Пересоздать дедлайны для договора на основе его дат.

        Returns:
            Количество созданных дедлайнов
        """
        cur = self.conn.cursor()

        # Получаем даты договора
        cur.execute("""
            SELECT performance_due, payment_due, end_date, initiator_user_id
            FROM contracts
            WHERE contract_id = %s
        """, (contract_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Договор {contract_id} не найден")

        performance_due, payment_due, end_date, initiator_user_id = row

        # Удаляем старые дедлайны
        cur.execute("""
            DELETE FROM calendar_deadlines
            WHERE entity_type = 'contract'
              AND entity_id = %s
              AND kind IN ('contract_execution_due', 'contract_payment_due', 'contract_end')
        """, (str(contract_id),))

        created = 0

        # Срок исполнения
        if performance_due:
            cur.execute("""
                INSERT INTO calendar_deadlines(
                    entity_type, entity_id, due_at, kind, title, description,
                    responsible_user_id, status, created_at
                )
                VALUES ('contract', %s, %s, 'contract_execution_due',
                        'Срок исполнения договора', 'Контроль выполнения обязательств',
                        %s, 'pending', NOW())
            """, (str(contract_id), performance_due, initiator_user_id))
            created += 1

        # Срок оплаты
        if payment_due:
            cur.execute("""
                INSERT INTO calendar_deadlines(
                    entity_type, entity_id, due_at, kind, title, description,
                    responsible_user_id, status, created_at
                )
                VALUES ('contract', %s, %s, 'contract_payment_due',
                        'Срок оплаты по договору', 'Контроль оплаты',
                        %s, 'pending', NOW())
            """, (str(contract_id), payment_due, initiator_user_id))
            created += 1

        # Дата окончания
        if end_date:
            cur.execute("""
                INSERT INTO calendar_deadlines(
                    entity_type, entity_id, due_at, kind, title, description,
                    responsible_user_id, status, created_at
                )
                VALUES ('contract', %s, %s, 'contract_end',
                        'Дата окончания договора', 'Проверить пролонгацию',
                        %s, 'pending', NOW())
            """, (str(contract_id), end_date, initiator_user_id))
            created += 1

        self.conn.commit()
        return created

    # =========================================================================
    # CRUD: получение и список договоров
    # =========================================================================
    def get_contract(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить договор по ID с полными данными:
        source_code, integration_1c_status, риски, отклонения, гарантия, ЕИС-статус.
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT
                c.contract_id, c.contract_no, c.title, c.type_code, c.status_code,
                c.sign_date, c.start_date, c.end_date, c.performance_due, c.payment_due,
                c.amount_total, c.currency, c.initiator_user_id, c.responsible_user_id,
                c.created_at, c.updated_at,
                c.source_code,
                c.integration_1c_status, c.integration_1c_error, c.integration_1c_sent_at,
                COALESCE(r.risks_cnt, 0)         AS risks_cnt,
                COALESCE(r.has_critical, FALSE)  AS has_critical_risk,
                COALESCE(d.deviations_cnt, 0)    AS deviations_cnt,
                COALESCE(g.has_guarantee, FALSE) AS has_active_guarantee,
                COALESCE(eis.status, 'not_sent') AS eis_status,
                eis.updated_at                   AS eis_updated_at
            FROM contracts c
            LEFT JOIN (
                SELECT contract_id,
                       COUNT(*) AS risks_cnt,
                       BOOL_OR(severity >= 4) AS has_critical
                FROM contract_risks
                WHERE resolved_at IS NULL
                GROUP BY contract_id
            ) r ON r.contract_id = c.contract_id
            LEFT JOIN (
                SELECT contract_id, COUNT(*) AS deviations_cnt
                FROM contract_template_deviations
                WHERE approved_at IS NULL
                GROUP BY contract_id
            ) d ON d.contract_id = c.contract_id
            LEFT JOIN (
                SELECT contract_id, TRUE AS has_guarantee
                FROM bank_guarantees
                WHERE status = 'active'
                GROUP BY contract_id
            ) g ON g.contract_id = c.contract_id
            LEFT JOIN LATERAL (
                SELECT status, updated_at
                FROM eis_export_queue
                WHERE contract_id = c.contract_id
                ORDER BY created_at DESC
                LIMIT 1
            ) eis ON TRUE
            WHERE c.contract_id = %s
        """, (contract_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "contract_id": row[0],
            "contract_no": row[1],
            "title": row[2],
            "type_code": row[3],
            "status_code": row[4],
            "sign_date": str(row[5]) if row[5] else None,
            "start_date": str(row[6]) if row[6] else None,
            "end_date": str(row[7]) if row[7] else None,
            "performance_due": str(row[8]) if row[8] else None,
            "payment_due": str(row[9]) if row[9] else None,
            "amount_total": float(row[10]) if row[10] else None,
            "currency": row[11],
            "initiator_user_id": row[12],
            "responsible_user_id": row[13],
            "created_at": str(row[14]),
            "updated_at": str(row[15]) if row[15] else None,
            "source_code": row[16] or "manual",
            "integration_1c_status": row[17] or "not_sent",
            "integration_1c_error": row[18],
            "integration_1c_sent_at": str(row[19]) if row[19] else None,
            "risks_cnt": row[20],
            "has_critical_risk": row[21],
            "deviations_cnt": row[22],
            "has_active_guarantee": row[23],
            "eis_status": row[24],
            "eis_updated_at": str(row[25]) if row[25] else None,
        }

    def list_contracts(
        self,
        status_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получить список договоров с индикаторами:
        source_code, has_active_guarantee, has_deviations, is_overdue_flag.
        """
        cur = self.conn.cursor()

        where_clause = ""
        params: List[Any] = []
        if status_code:
            where_clause = "WHERE c.status_code = %s"
            params.append(status_code)

        params.extend([limit, offset])

        cur.execute(f"""
            SELECT
                c.contract_id, c.contract_no, c.title, c.status_code,
                c.end_date, c.amount_total,
                c.source_code,
                CASE
                    WHEN c.end_date IS NOT NULL
                     AND c.end_date < CURRENT_DATE
                     AND c.status_code NOT IN ('completed','terminated','archived','overdue')
                    THEN TRUE ELSE FALSE
                END AS is_overdue_flag,
                EXISTS(
                    SELECT 1 FROM bank_guarantees bg
                    WHERE bg.contract_id = c.contract_id AND bg.status = 'active'
                ) AS has_active_guarantee,
                EXISTS(
                    SELECT 1 FROM contract_template_deviations d
                    WHERE d.contract_id = c.contract_id AND d.approved_at IS NULL
                ) AS has_deviations
            FROM contracts c
            {where_clause}
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
        """, params)

        return [
            {
                "contract_id": row[0],
                "contract_no": row[1],
                "title": row[2],
                "status_code": row[3],
                "end_date": str(row[4]) if row[4] else None,
                "amount_total": float(row[5]) if row[5] else None,
                "source_code": row[6] or "manual",
                "is_overdue_flag": row[7],
                "has_active_guarantee": row[8],
                "has_deviations": row[9],
            }
            for row in cur.fetchall()
        ]

    # =========================================================================
    # 11) Таймлайн (история изменений договора)
    # =========================================================================
    def get_timeline(self, contract_id: int) -> List[Dict[str, Any]]:
        """
        Получить историю изменений договора из contract_history.

        Returns:
            [{"history_id", "field_name", "old_value", "new_value",
              "changed_by", "changed_at", "reason"}, ...]
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT history_id, field_name, old_value, new_value,
                   changed_by, changed_at, reason
            FROM contract_history
            WHERE contract_id = %s
            ORDER BY changed_at DESC
        """, (contract_id,))
        return [
            {
                "history_id": row[0],
                "field_name": row[1],
                "old_value": row[2],
                "new_value": row[3],
                "changed_by": row[4],
                "changed_at": str(row[5]),
                "reason": row[6],
            }
            for row in cur.fetchall()
        ]

    # =========================================================================
    # 12) ИИ-анализ: получение последнего результата
    # =========================================================================
    def get_latest_analysis(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить последний ИИ-анализ для договора.

        Returns:
            dict или None если анализ не проводился
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT analysis_id, status, analyzed_by, analyzed_at,
                   document_version, deviations_count, has_critical_risk,
                   summary_text, details_json, created_at, updated_at
            FROM contract_analyses
            WHERE contract_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (contract_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "analysis_id": row[0],
            "status": row[1],
            "analyzed_by": row[2],
            "analyzed_at": str(row[3]) if row[3] else None,
            "document_version": row[4],
            "deviations_count": row[5],
            "has_critical_risk": row[6],
            "summary_text": row[7],
            "details_json": row[8],
            "created_at": str(row[9]),
            "updated_at": str(row[10]) if row[10] else None,
        }

    # =========================================================================
    # 13) ИИ-анализ: запуск нового анализа
    # =========================================================================
    def start_analysis(self, contract_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Запустить ИИ-анализ договора.

        - Создаёт запись в contract_analyses
        - Вычисляет реальные показатели из БД (отклонения, критические риски)
        - Формирует итоговое резюме

        Returns:
            {"analysis_id": int, "status": str}
        """
        cur = self.conn.cursor()

        # Проверяем существование договора
        cur.execute("SELECT 1 FROM contracts WHERE contract_id = %s", (contract_id,))
        if not cur.fetchone():
            raise ValueError(f"Договор {contract_id} не найден")

        # Отмечаем предыдущий активный анализ как needs_rerun (если был)
        cur.execute("""
            UPDATE contract_analyses
            SET status = 'needs_rerun', updated_at = NOW()
            WHERE contract_id = %s AND status IN ('pending', 'running')
        """, (contract_id,))

        # Считаем реальные данные из БД
        cur.execute("""
            SELECT
                COUNT(*)                           AS deviations_count,
                FALSE                              AS has_critical_risk
            FROM contract_template_deviations
            WHERE contract_id = %s AND approved_at IS NULL
        """, (contract_id,))
        dev_row = cur.fetchone()
        deviations_count = dev_row[0] if dev_row else 0

        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM contract_risks
                WHERE contract_id = %s AND resolved_at IS NULL AND severity >= 4
            )
        """, (contract_id,))
        crit_row = cur.fetchone()
        has_critical_risk = crit_row[0] if crit_row else False

        cur.execute("""
            SELECT COUNT(*) FROM contract_risks
            WHERE contract_id = %s AND resolved_at IS NULL
        """, (contract_id,))
        risks_row = cur.fetchone()
        risks_count = risks_row[0] if risks_row else 0

        # Формируем резюме
        parts = []
        if deviations_count > 0:
            parts.append(f"Найдено {deviations_count} отклонений от шаблона")
        else:
            parts.append("Отклонений от шаблона не обнаружено")

        if has_critical_risk:
            parts.append(f"Обнаружено критических рисков: {risks_count} — рекомендуется проверка")
        elif risks_count > 0:
            parts.append(f"Потенциальных рисков: {risks_count} — рекомендуется проверить")
        else:
            parts.append("Критичных рисков не выявлено")

        summary_text = ". ".join(parts)

        # Создаём завершённую запись анализа
        cur.execute("""
            INSERT INTO contract_analyses(
                contract_id, status, analyzed_by, analyzed_at,
                deviations_count, has_critical_risk, summary_text,
                created_at, updated_at
            )
            VALUES (%s, 'done', %s, NOW(), %s, %s, %s, NOW(), NOW())
            RETURNING analysis_id
        """, (contract_id, user_id, deviations_count, has_critical_risk, summary_text))
        analysis_id = cur.fetchone()[0]

        # Фиксируем в истории
        cur.execute("""
            INSERT INTO contract_history(
                contract_id, field_name, old_value, new_value, changed_by, changed_at, reason
            )
            VALUES (%s, 'ai_analysis', NULL, 'done', %s, NOW(), 'ИИ-анализ выполнен')
        """, (contract_id, user_id))

        self.conn.commit()
        return {"analysis_id": analysis_id, "status": "done"}

    # =========================================================================
    # 14) Отправка договора в 1С (исходящая интеграция)
    # =========================================================================
    def send_to_1c(self, contract_id: int) -> Dict[str, Any]:
        """
        Поставить договор в очередь исходящей отправки в 1С.

        Идемпотентно: повторная отправка не создаёт дубликат job.
        Ошибка интеграции не меняет статус самого договора.

        Returns:
            {"status": str, "job_id": str | None, "message": str | None}
        """
        cur = self.conn.cursor()

        # Получаем текущий статус интеграции
        cur.execute("""
            SELECT integration_1c_status
            FROM contracts
            WHERE contract_id = %s
        """, (contract_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Договор {contract_id} не найден")

        current_status = row[0]

        # Идемпотентность: уже отправлен — возвращаем без изменений
        if current_status == "sent":
            return {"status": "sent", "job_id": None, "message": "Договор уже отправлен в 1С"}

        # Идемпотентность: уже в очереди — возвращаем без дубликата
        if current_status == "queued":
            return {"status": "queued", "job_id": None, "message": "Договор уже в очереди на отправку в 1С"}

        # Обновляем статус интеграции на 'queued'
        cur.execute("""
            UPDATE contracts
            SET integration_1c_status = 'queued',
                integration_1c_error = NULL,
                updated_at = NOW()
            WHERE contract_id = %s
        """, (contract_id,))

        # Создаём job для воркера
        job_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO jobs(
                id, type, payload_json, run_at, status, attempts, idempotency_key, created_at
            )
            VALUES (%s, 'send_1c_contract', %s, NOW(), 'pending', 0, %s, NOW())
        """, (job_id, json.dumps({"contract_id": contract_id}), f"1c_out:{contract_id}"))

        # Фиксируем в истории договора
        cur.execute("""
            INSERT INTO contract_history(
                contract_id, field_name, old_value, new_value, changed_at, reason
            )
            VALUES (%s, 'integration_1c_status', %s, 'queued', NOW(),
                    'Пользователь инициировал отправку в 1С')
        """, (contract_id, current_status))

        self.conn.commit()
        return {"status": "queued", "job_id": job_id, "message": None}
