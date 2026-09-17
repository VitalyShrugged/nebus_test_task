from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.project.schemas.api.payments import PaymentCreateRequest, PaymentDBData, PaymentResponse


class TestPaymentCreateRequest:
    def test_valid_payload_parses_correctly(self) -> None:
        request = PaymentCreateRequest(
            amount=Decimal("199.99"),
            currency="RUB",
            description="Order #42",
            metadata={"order_id": 42},
            webhook_url="https://example.com/webhook",
        )
        assert request.amount == Decimal("199.99")
        assert request.currency == "RUB"
        assert request.metadata == {"order_id": 42}

    def test_optional_fields_default_to_none(self) -> None:
        request = PaymentCreateRequest(
            amount=Decimal("1.00"), currency="USD", webhook_url="https://example.com/webhook",
        )
        assert request.description is None
        assert request.metadata is None

    @pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1"), Decimal("-0.01")])
    def test_non_positive_amount_is_rejected(self, amount: Decimal) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(amount=amount, currency="RUB", webhook_url="https://example.com/webhook")

    def test_invalid_currency_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(
                amount=Decimal("1.00"), currency="GBP", webhook_url="https://example.com/webhook",  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize("webhook_url", ["not-a-url", "ftp:/broken", ""])
    def test_invalid_webhook_url_is_rejected(self, webhook_url: str) -> None:
        with pytest.raises(ValidationError, match="webhook_url"):
            PaymentCreateRequest(amount=Decimal("1.00"), currency="RUB", webhook_url=webhook_url)

    def test_valid_webhook_url_is_accepted(self) -> None:
        request = PaymentCreateRequest(
            amount=Decimal("1.00"), currency="RUB", webhook_url="https://example.com/webhook",
        )
        assert request.webhook_url == "https://example.com/webhook"


class TestPaymentResponse:
    def test_amount_is_serialized_as_float(self) -> None:
        response = PaymentResponse(
            payment_id="p1",
            amount=Decimal("199.99"),
            currency="RUB",
            status="succeeded",
            webhook_url="https://example.com/webhook",
            created_at=datetime.now(timezone.utc),
        )
        dumped = response.model_dump()
        assert dumped["amount"] == 199.99
        assert isinstance(dumped["amount"], float)

    def test_processed_at_defaults_to_none(self) -> None:
        response = PaymentResponse(
            payment_id="p1",
            amount=Decimal("1.00"),
            currency="RUB",
            status="pending",
            webhook_url="https://example.com/webhook",
            created_at=datetime.now(timezone.utc),
        )
        assert response.processed_at is None


class TestPaymentDBData:
    def _base_kwargs(self) -> dict:
        return {
            "payment_id": "p1",
            "amount": Decimal("1.00"),
            "currency": "RUB",
            "status": "pending",
            "idempotency_key": "key-1",
            "webhook_url": "https://example.com/webhook",
            "created_at": datetime.now(timezone.utc),
        }

    def test_metadata_json_string_is_parsed_into_dict(self) -> None:
        payment = PaymentDBData(**self._base_kwargs(), metadata='{"order_id": 42}')  # type: ignore[arg-type]
        assert payment.metadata == {"order_id": 42}

    def test_metadata_dict_passes_through_unchanged(self) -> None:
        payment = PaymentDBData(**self._base_kwargs(), metadata={"order_id": 42})
        assert payment.metadata == {"order_id": 42}

    def test_metadata_invalid_json_string_becomes_none(self) -> None:
        payment = PaymentDBData(**self._base_kwargs(), metadata="not-json")  # type: ignore[arg-type]
        assert payment.metadata is None

    def test_metadata_none_stays_none(self) -> None:
        payment = PaymentDBData(**self._base_kwargs(), metadata=None)
        assert payment.metadata is None
