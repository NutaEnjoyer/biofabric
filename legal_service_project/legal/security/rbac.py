"""RBAC для Legal Service.

Роли:
  legal_admin  — полный доступ
  legal_user   — создание/редактирование договоров, интеграции, ИИ-анализ
  legal_viewer — только чтение

Матрица действий:
  view_contract      — viewer, user, admin
  edit_contract      — user, admin
  bind_workflow      — user, admin
  send_to_1c         — user, admin
  send_to_eis        — user, admin
  start_ai_analysis  — user, admin
  sync_deadlines     — user, admin
  send_notification  — user, admin
  import_1c          — admin
  mark_overdue       — admin
"""

ROLE_MATRIX: dict[str, list[str]] = {
    "view_contract":     ["legal_viewer", "legal_user", "legal_admin"],
    "edit_contract":     ["legal_user", "legal_admin"],
    "bind_workflow":     ["legal_user", "legal_admin"],
    "send_to_1c":        ["legal_user", "legal_admin"],
    "send_to_eis":       ["legal_user", "legal_admin"],
    "start_ai_analysis": ["legal_user", "legal_admin"],
    "sync_deadlines":    ["legal_user", "legal_admin"],
    "send_notification": ["legal_user", "legal_admin"],
    "import_1c":         ["legal_admin"],
    "mark_overdue":      ["legal_admin"],
}


def can(user, action: str) -> bool:
    """Проверить, разрешено ли пользователю выполнить действие."""
    roles = getattr(user, "roles", [])
    allowed = ROLE_MATRIX.get(action, [])
    return any(r in allowed for r in roles)
