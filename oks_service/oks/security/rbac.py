"""RBAC для OKS Service.

Роли:
  oks_admin       — полный доступ
  oks_responsible — редактирование своих объектов и этапов
  oks_initiator   — просмотр и комментарии по инициированным объектам
  oks_viewer      — только чтение

Матрица действий:
  view_object      — viewer, initiator, responsible, admin
  create_object    — responsible, admin
  edit_object      — responsible, admin
  delete_object    — admin
  manage_stages    — responsible, admin
  manage_documents — responsible, admin
  add_comment      — initiator, responsible, admin
  manage_all       — admin
"""

ROLE_MATRIX: dict[str, list[str]] = {
    "view_object":      ["oks_viewer", "oks_initiator", "oks_responsible", "oks_admin"],
    "create_object":    ["oks_responsible", "oks_admin"],
    "edit_object":      ["oks_responsible", "oks_admin"],
    "delete_object":    ["oks_admin"],
    "manage_stages":    ["oks_responsible", "oks_admin"],
    "manage_documents": ["oks_responsible", "oks_admin"],
    "add_comment":      ["oks_initiator", "oks_responsible", "oks_admin"],
    "manage_all":       ["oks_admin"],
}


def can(user, action: str) -> bool:
    roles = getattr(user, "roles", [])
    allowed = ROLE_MATRIX.get(action, [])
    return any(r in allowed for r in roles)
