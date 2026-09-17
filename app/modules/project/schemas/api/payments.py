import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import ConfigDict, Field, HttpUrl, field_serializer, field_validator

from app.modules.project.schemas.api.base import CustomBaseModel


PaymentCurrency = Literal["RUB", "USD", "EUR"]
PaymentStatus = Literal["pending", "succeeded", "failed"]


class PaymentCreateRequest(CustomBaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "199.99",
                "currency": "RUB",
                "description": "Order #42",
                "metadata": {"order_id": 42},
                "webhook_url": "https://example.com/webhook",
            },
        },
    )

    amount: Decimal = Field(..., gt=0, description="Сумма платежа.")
    currency: PaymentCurrency = Field(..., description="Валюта платежа.")
    description: str | None = Field(default=None, description="Описание платежа.")
    metadata: dict[str, Any] | None = Field(default=None, description="Дополнительные метаданные платежа.")
    webhook_url: str = Field(..., description="URL для отправки webhook-уведомления о результате обработки платежа.")

    @field_validator("webhook_url")
    @classmethod
    def _validate_webhook_url(cls, value: str) -> str:
        try:
            HttpUrl(value)
        except Exception as e:
            raise ValueError(f"Некорректный webhook_url: {e}")
        return value


class PaymentCreateResponse(CustomBaseModel):
    payment_id: str = Field(..., description="Уникальный идентификатор платежа.")
    status: PaymentStatus = Field(..., description="Текущий статус платежа.")
    created_at: datetime = Field(..., description="Дата создания платежа.")


class PaymentResponse(CustomBaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "payment_id": "27ea6b8f-17fa-4a7b-a9f6-31b8dc76abe4",
                "amount": 199.99,
                "currency": "RUB",
                "description": "Order #42",
                "metadata": {"order_id": 42},
                "status": "succeeded",
                "webhook_url": "https://example.com/webhook",
                "created_at": "2026-09-17T11:38:44.037751Z",
                "processed_at": "2026-09-17T11:38:47.512340Z",
            },
        },
    )

    payment_id: str = Field(..., description="Уникальный идентификатор платежа.")
    amount: Decimal = Field(..., description="Сумма платежа.")
    currency: PaymentCurrency = Field(..., description="Валюта платежа.")
    description: str | None = Field(default=None, description="Описание платежа.")
    metadata: dict[str, Any] | None = Field(default=None, description="Дополнительные метаданные платежа.")
    status: PaymentStatus = Field(..., description="Текущий статус платежа.")
    webhook_url: str = Field(..., description="URL для отправки webhook-уведомления о результате обработки платежа.")
    created_at: datetime = Field(..., description="Дата создания платежа.")
    processed_at: datetime | None = Field(default=None, description="Дата обработки платежа.")

    @field_serializer("amount")
    def _serialize_amount(self, value: Decimal) -> float:
        return float(value)


class PaymentDBData(CustomBaseModel):
    payment_id: str = Field(..., description="Уникальный идентификатор платежа.")
    amount: Decimal = Field(..., description="Сумма платежа.")
    currency: PaymentCurrency = Field(..., description="Валюта платежа.")
    description: str | None = Field(default=None, description="Описание платежа.")
    metadata: dict[str, Any] | None = Field(default=None, description="Дополнительные метаданные платежа.")
    status: PaymentStatus = Field(..., description="Текущий статус платежа.")
    idempotency_key: str = Field(..., description="Ключ идемпотентности.")
    webhook_url: str = Field(..., description="URL для отправки webhook-уведомления о результате обработки платежа.")
    created_at: datetime = Field(..., description="Дата создания платежа.")
    processed_at: datetime | None = Field(default=None, description="Дата обработки платежа.")

    @field_validator("metadata", mode="before")
    @classmethod
    def _parse_metadata(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value
