
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class RoleEnum(str, enum.Enum):
    initiator = "Инициатор"
    warehouse = "Склад"
    director = "Директор"
    head_of_procurement = "Начальник ОЗ"
    buyer = "Исполнитель ОЗ"
    legal = "Юротдел"
    accounting = "Бухгалтерия"

class StatusEnum(str, enum.Enum):
    draft = "Черновик"
    on_approval = "На согласовании"
    in_progress = "На исполнении"
    awaiting_delivery = "Ожидание поставки"
    done = "Исполнена"
    overdue = "Просрочка"

STATUS_COLOR = {
    StatusEnum.draft: "grey",
    StatusEnum.on_approval: "yellow",
    StatusEnum.in_progress: "skyblue",
    StatusEnum.awaiting_delivery: "orange",
    StatusEnum.done: "green",
    StatusEnum.overdue: "red",
}

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    fio = Column(String, nullable=False)
    department = Column(String, nullable=True)
    position = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), nullable=False)

class OneCStatusEnum(str, enum.Enum):
    not_sent = "not_sent"
    queued   = "queued"
    sent     = "sent"
    error    = "error"

class ProcurementRequest(Base):
    __tablename__ = "procurement_requests"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)  # предмет закупки
    justification = Column(Text, nullable=True)  # обоснование
    status = Column(Enum(StatusEnum), default=StatusEnum.draft, nullable=False)
    onec_status = Column(Enum(OneCStatusEnum), default=OneCStatusEnum.not_sent, nullable=False)  # статус исходящей интеграции

    initiator = relationship("User")
    items = relationship("RequestItem", back_populates="request", cascade="all, delete")
    approvals = relationship("Approval", back_populates="request", cascade="all, delete")
    quotes = relationship("SupplierQuote", back_populates="request", cascade="all, delete")
    documents = relationship("Document", back_populates="request", cascade="all, delete")
    events = relationship("Event", back_populates="request", cascade="all, delete")

class RequestItem(Base):
    __tablename__ = "request_items"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("procurement_requests.id"))
    nomenclature = Column(String, nullable=False)  # номенклатура
    tech_spec = Column(Text, nullable=True)        # ТХ
    due_days = Column(Integer, nullable=True)      # срок
    quantity = Column(Float, nullable=False)
    justification = Column(Text, nullable=True)

    request = relationship("ProcurementRequest", back_populates="items")

class ApprovalDecisionEnum(str, enum.Enum):
    approve = "Утвердить"
    reject = "Отклонить"
    return_for_rework = "Вернуть на доработку"

class Approval(Base):
    __tablename__ = "approvals"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("procurement_requests.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    decision = Column(Enum(ApprovalDecisionEnum), nullable=False)
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), server_default=func.now())

    request = relationship("ProcurementRequest", back_populates="approvals")
    user = relationship("User")

class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("procurement_requests.id"))
    supplier_name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    delivery_days = Column(Integer, nullable=True)
    payment_terms = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    file_ref = Column(String, nullable=True)  # путь/ид файла
    is_selected = Column(Boolean, default=False, nullable=False)  # победитель тендера

    request = relationship("ProcurementRequest", back_populates="quotes")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("procurement_requests.id"))
    doc_type = Column(String, nullable=False)  # договор, счёт, акт, накладная, ТЗ, КП
    filename = Column(String, nullable=False)
    storage_url = Column(String, nullable=True)  # имитация хранения
    signed = Column(Boolean, default=False)

    request = relationship("ProcurementRequest", back_populates="documents")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("procurement_requests.id"), nullable=True)  # nullable для системных событий
    event_type = Column(String, nullable=False)  # created, status_changed, approval_given, user_synced etc.
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    request = relationship("ProcurementRequest", back_populates="events")
