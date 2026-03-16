from pydantic import BaseModel, Field
from typing import Optional, List


class PostCreate(BaseModel):
    channel_id: int
    format_id: int
    topic_id: int
    direction_id: Optional[int] = None
    title: Optional[str] = None
    text: Optional[str] = Field(None, description="Основной текст поста (сохраняется в mk_post_contents.body_md)")
    planned_for: Optional[str] = Field(None, description="Дата публикации YYYY-MM-DD")
    # ТЗ п.1: источник контента
    source_code: Optional[str] = Field("manual", description="Источник: manual | ai_generated | external_source | archive")
    # ТЗ п.5: целевая аудитория, цели, тон
    audience: Optional[str] = Field(None, description="Целевая аудитория")
    goals: Optional[str] = Field(None, description="Цели публикации (имиджевые/информационные/рекламные)")
    tone: Optional[str] = Field(None, description="Tone of voice / стиль")
    # ТЗ п.6: хэштеги
    hashtags: Optional[List[str]] = Field(None, description="Хэштеги (#тег)")
    document_ids: Optional[List[int]] = Field(None, description="ID документов ООК для привязки к посту")


class PostUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    planned_for: Optional[str] = None
    channel_id: Optional[int] = None
    format_id: Optional[int] = None
    topic_id: Optional[int] = None
    direction_id: Optional[int] = None
    audience: Optional[str] = None
    goals: Optional[str] = None
    tone: Optional[str] = None
    hashtags: Optional[List[str]] = None


class PostRead(BaseModel):
    post_id: int
    status_code: str
    source_code: str = "manual"
    channel_id: Optional[int] = None
    format_id: Optional[int] = None
    topic_id: Optional[int] = None
    direction_id: Optional[int] = None
    title: Optional[str] = None
    body_md: Optional[str] = None
    hashtags: Optional[List[str]] = None
    planned_for: Optional[str] = None
    audience: Optional[str] = None
    goals: Optional[str] = None
    tone: Optional[str] = None
    external_url: Optional[str] = None


class PublishNowRequest(BaseModel):
    platform: str  # 'tg' | 'vk'


class PublishNowResponse(BaseModel):
    ok: bool = True
    external_url: Optional[str] = None
    error_message: Optional[str] = None


class ReplacePostRequest(BaseModel):
    date: str
    post_id_to_remove: int
    idea_post_id_to_use: int  # post in draft without date


# ─── ИИ-операции над постом (ТЗ п.2.2) ──────────────────────────────────────

class AIPostTextRequest(BaseModel):
    """Параметры для генерации / рерайта текста поста."""
    style_hint: Optional[str] = Field(None, description="Подсказка по стилю / tone of voice")
    extra_context: Optional[str] = Field(None, description="Дополнительный контекст для генерации")


class AIPostTextResponse(BaseModel):
    """Предложенный ИИ текст (не применяется автоматически)."""
    title: Optional[str] = None
    body_md: str
    hashtags: Optional[List[str]] = None
    disclaimer: str = "Материалы, сформированные ИИ, подлежат обязательной проверке и утверждению"
