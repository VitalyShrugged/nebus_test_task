import json
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.modules.project.schemas.api.base import CustomBaseModel


OutboxEventStatus = Literal["pending", "published", "failed"]


class OutboxEventDBData(CustomBaseModel):
    # table outbox
    id: int = Field(..., description="Идентификатор события в outbox.")
    aggregate_type: str = Field(..., description="Тип сущности-источника события.")
    aggregate_id: str = Field(..., description="Идентификатор сущности-источника события.")
    event_type: str = Field(..., description="Тип события (например, payments.new).")
    payload: dict[str, Any] = Field(..., description="Полезная нагрузка события.")
    status: OutboxEventStatus = Field(..., description="Статус публикации события.")
    attempts: int = Field(..., description="Количество попыток публикации.")
    last_error: str | None = Field(default=None, description="Текст последней ошибки публикации.")
    created_at: datetime = Field(..., description="Дата создания события.")
    processed_at: datetime | None = Field(default=None, description="Дата успешной публикации события.")

    @field_validator("payload", mode="before")
    @classmethod
    def _parse_payload(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value)
        return value
