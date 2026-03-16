"""Связь с документами ядра (медиа/вложения)."""
from ..core_client.client import CoreClient

class DocumentsService:
    def __init__(self, core: CoreClient) -> None:
        self.core = core

    async def bind(self, entity_type: str, entity_id: str, document_id: int) -> None:
        """Привязать документ к посту (медиа/бриф)."""
        await self.core.bind_document(entity_type, entity_id, document_id)
