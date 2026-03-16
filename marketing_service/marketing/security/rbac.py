"""RBAC: примитивная проверка прав.

На старте достаточно ролей: author, reviewer, approver, publisher, admin.
"""


def can(user, action: str, resource: str) -> bool:
    if "admin" in getattr(user, "roles", []):
        return True
    # Упростим: автор может CRUD draft, ревьюер/аппрувер — менять статусы, публикатор — публиковать.
    matrix = {
        "create_post": ["author", "admin"],
        "update_post": ["author", "admin"],
        "send_to_review": ["author", "admin"],
        "return_to_draft": ["reviewer", "admin"],
        "approve": ["approver", "admin"],
        "publish": ["publisher", "admin"],
        "archive": ["admin"],
    }
    allowed = matrix.get(action, [])
    return any(role in getattr(user, "roles", []) for role in allowed)
