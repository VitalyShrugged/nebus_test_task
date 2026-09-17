from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.db.postgres.models.base import Base


class OutboxEvent(Base):
    """
    Событие для гарантированной публикации в RabbitMQ (Outbox pattern).
    Пишется в той же транзакции, что и породившая его сущность (например, платёж),
    и рассылается отдельным релеем, который опрашивает status = 'pending'.
    """

    __tablename__ = "outbox"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'published', 'failed')", name="ck_outbox_status"),
        # Совпадает с реальным запросом релея: WHERE status = 'pending' ORDER BY id
        Index("ix_outbox_status_id", "status", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
