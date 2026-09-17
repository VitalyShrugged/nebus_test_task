from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.db.postgres.models.base import Base


class Payment(Base):
    """
    Платёж. payment_id и idempotency_key хранятся как строки (а не native UUID),
    чтобы совпадать с текущим слоем доступа к БД (raw SQL + asyncpg), который
    генерирует идентификаторы на стороне приложения через uuid.uuid4().
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("currency IN ('RUB', 'USD', 'EUR')", name="ck_payments_currency"),
        CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name="ck_payments_status"),
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        # Под операционные запросы вида "зависшие в pending дольше N минут", дашборды по статусам и т.п.
        Index("ix_payments_status_created_at", "status", "created_at"),
    )

    payment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB().with_variant(JSON, "sqlite"), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
