-- Legal Service — Schema Snapshot
-- Основные таблицы определены в database/v5_legal.sql
-- Этот файл — справочный снимок структуры для модуля.

-- Зависимости от ядра:
-- - app_users (v1_core_schema.sql)
-- - documents, document_templates (v2_ook_docflow.sql)
-- - workflow_definitions, workflow_instances (v1_core_schema_delta.sql)
-- - calendar_deadlines (v1_core_schema_delta.sql)
-- - jobs (v1_core_schema_delta.sql)
-- - notifications_outbox, notification_templates (v1_core_schema.sql + delta)

-- ============================================================================
-- ОСНОВНЫЕ ТАБЛИЦЫ (v5_legal.sql)
-- ============================================================================

-- contract_statuses: статусы жизненного цикла договоров
-- contract_types: типы/виды договоров
-- contracts: реестр договоров
-- contract_parties: стороны договора (customer/supplier/guarantor/other)
-- contract_risk_types: типы рисков
-- contract_risks: выявленные риски
-- contract_template_deviations: отклонения от шаблона
-- bank_guarantee_statuses: статусы гарантий
-- bank_guarantees: банковские гарантии
-- contract_workflow_bind: привязка к workflow
-- contract_documents: дополнительные документы
-- contract_history: история изменений

-- ============================================================================
-- ТАБЛИЦЫ ИНТЕГРАЦИЙ (v6_legal_delta.sql)
-- ============================================================================

-- eis_export_queue: очередь экспорта в ЕИС
-- eis_export_log: лог обмена с ЕИС
-- import_contracts_1c: стейджинг импорта из 1С

-- ============================================================================
-- VIEW (v5_legal.sql + v6_legal_delta.sql)
-- ============================================================================

-- v_contracts_with_guarantee: KPI по гарантиям
-- v_contracts_overdue: просроченные договоры
-- v_contracts_issues: сводка рисков и отклонений
-- v_contracts_without_guarantee: договоры без гарантии
-- v_contracts_by_status: статистика по статусам
-- v_bank_guarantees_expiring_30d: истекающие гарантии

-- ============================================================================
-- ФУНКЦИИ (v6_legal_delta.sql)
-- ============================================================================

-- sync_contract_deadlines(): триггер синхронизации дедлайнов
-- mark_contract_overdue(): пометить просроченные договоры
-- enqueue_eis_send(queue_id): поставить в очередь ЕИС
-- audit_contract_action(...): записать в аудит
