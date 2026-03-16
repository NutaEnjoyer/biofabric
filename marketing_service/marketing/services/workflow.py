"""Workflow-обёртки: перевод статусов через ядро."""
from ..core_client.client import CoreClient

class WorkflowService:
    def __init__(self, core: CoreClient) -> None:
        self.core = core

    async def advance(self, entity_type: str, entity_id: str, transition: str) -> None:
        """Делегирует перевод статуса в ядро, чтобы все модули были консистентны."""
        await self.core.advance_workflow(entity_type, entity_id, transition)
