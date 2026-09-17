from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import ANY, AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.modules.project.http_errors import HTTP_ERRORS
from app.modules.project.schemas.api.payments import PaymentDBData

ROUTE_MODULE = "app.fastapi_server.routes.project.payments"


@pytest.fixture
def sample_payment() -> PaymentDBData:
    return PaymentDBData(
        payment_id="27ea6b8f-17fa-4a7b-a9f6-31b8dc76abe4",
        amount=Decimal("199.99"),
        currency="RUB",
        description="Order #42",
        metadata={"order_id": 42},
        status="pending",
        idempotency_key="test-idempotency-key",
        webhook_url="https://example.com/webhook",
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        processed_at=None,
    )


class TestCreatePayment:
    async def test_create_payment_success(
            self, test_client: AsyncClient, api_key_headers: dict, sample_payment: PaymentDBData,
    ) -> None:
        with (
            patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock(return_value=sample_payment)) as create_mock,
            patch(f"{ROUTE_MODULE}.create_outbox_event", new=AsyncMock()) as outbox_mock,
        ):
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={
                    "amount": "199.99",
                    "currency": "RUB",
                    "description": "Order #42",
                    "metadata": {"order_id": 42},
                    "webhook_url": "https://example.com/webhook",
                },
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data == {
            "payment_id": sample_payment.payment_id,
            "status": "pending",
            "created_at": "2026-01-01T12:00:00Z",
        }

        create_mock.assert_called_once()
        outbox_mock.assert_called_once_with(
            aggregate_type="payment",
            aggregate_id=sample_payment.payment_id,
            event_type="payments.new",
            payload={
                "payment_id": sample_payment.payment_id,
                "amount": "199.99",
                "currency": "RUB",
                "description": "Order #42",
                "metadata": {"order_id": 42},
                "webhook_url": "https://example.com/webhook",
                "created_at": sample_payment.created_at.isoformat(),
            },
            project_db_session=ANY,
        )

    async def test_create_payment_idempotent_replay_returns_existing_payment(
            self, test_client: AsyncClient, api_key_headers: dict, sample_payment: PaymentDBData,
    ) -> None:
        # create_payment вернул None — конфликт по idempotency_key (ON CONFLICT DO NOTHING)
        with (
            patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock(return_value=None)),
            patch(f"{ROUTE_MODULE}.create_outbox_event", new=AsyncMock()) as outbox_mock,
            patch(
                f"{ROUTE_MODULE}.get_payment_by_idempotency_key", new=AsyncMock(return_value=sample_payment),
            ) as get_by_key_mock,
        ):
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={"amount": "199.99", "currency": "RUB", "webhook_url": "https://example.com/webhook"},
            )

        assert resp.status_code == 202
        assert resp.json()["payment_id"] == sample_payment.payment_id
        get_by_key_mock.assert_called_once()
        # повторный запрос не должен публиковать новое outbox-событие
        outbox_mock.assert_not_called()

    async def test_create_payment_fails_if_no_payment_created_or_found(
            self, test_client: AsyncClient, api_key_headers: dict,
    ) -> None:
        with (
            patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock(return_value=None)),
            patch(f"{ROUTE_MODULE}.create_outbox_event", new=AsyncMock()),
            patch(f"{ROUTE_MODULE}.get_payment_by_idempotency_key", new=AsyncMock(return_value=None)),
        ):
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={"amount": "199.99", "currency": "RUB", "webhook_url": "https://example.com/webhook"},
            )

        assert resp.status_code == HTTP_ERRORS["payment_create_error"].status_code
        assert resp.json()["detail"] == HTTP_ERRORS["payment_create_error"].detail

    async def test_create_payment_without_idempotency_key_header(
            self, test_client: AsyncClient, api_key_headers: dict,
    ) -> None:
        with patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock()) as create_mock:
            resp = await test_client.post(
                "/api/v1/payments",
                headers=api_key_headers,
                json={"amount": "199.99", "currency": "RUB", "webhook_url": "https://example.com/webhook"},
            )

        assert resp.status_code == 422
        create_mock.assert_not_called()

    async def test_create_payment_without_api_key(self, test_client: AsyncClient) -> None:
        resp = await test_client.post(
            "/api/v1/payments",
            headers={"Idempotency-Key": "test-idempotency-key"},
            json={"amount": "199.99", "currency": "RUB", "webhook_url": "https://example.com/webhook"},
        )
        assert resp.status_code == 422

    async def test_create_payment_with_wrong_api_key(self, test_client: AsyncClient) -> None:
        resp = await test_client.post(
            "/api/v1/payments",
            headers={"X-API-Key": "wrong-key", "Idempotency-Key": "test-idempotency-key"},
            json={"amount": "199.99", "currency": "RUB", "webhook_url": "https://example.com/webhook"},
        )
        assert resp.status_code == HTTP_ERRORS["invalid_api_key"].status_code
        assert resp.json()["detail"] == HTTP_ERRORS["invalid_api_key"].detail

    @pytest.mark.parametrize("currency", ["USD", "RUB", "EUR"])
    async def test_create_payment_accepts_supported_currencies(
            self, test_client: AsyncClient, api_key_headers: dict, sample_payment: PaymentDBData, currency: str,
    ) -> None:
        with (
            patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock(return_value=sample_payment)),
            patch(f"{ROUTE_MODULE}.create_outbox_event", new=AsyncMock()),
        ):
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={"amount": "1.00", "currency": currency, "webhook_url": "https://example.com/webhook"},
            )
        assert resp.status_code == 202

    async def test_create_payment_with_invalid_currency(
            self, test_client: AsyncClient, api_key_headers: dict,
    ) -> None:
        with patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock()) as create_mock:
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={"amount": "1.00", "currency": "GBP", "webhook_url": "https://example.com/webhook"},
            )
        assert resp.status_code == 422
        create_mock.assert_not_called()

    @pytest.mark.parametrize("amount", ["0", "-1.00", "-0.01"])
    async def test_create_payment_with_non_positive_amount(
            self, test_client: AsyncClient, api_key_headers: dict, amount: str,
    ) -> None:
        with patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock()) as create_mock:
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={"amount": amount, "currency": "RUB", "webhook_url": "https://example.com/webhook"},
            )
        assert resp.status_code == 422
        create_mock.assert_not_called()

    async def test_create_payment_with_invalid_webhook_url(
            self, test_client: AsyncClient, api_key_headers: dict,
    ) -> None:
        with patch(f"{ROUTE_MODULE}.create_payment", new=AsyncMock()) as create_mock:
            resp = await test_client.post(
                "/api/v1/payments",
                headers={**api_key_headers, "Idempotency-Key": "test-idempotency-key"},
                json={"amount": "1.00", "currency": "RUB", "webhook_url": "not-a-url"},
            )
        assert resp.status_code == 422
        create_mock.assert_not_called()


class TestGetPayment:
    async def test_get_payment_found(
            self, test_client: AsyncClient, api_key_headers: dict, sample_payment: PaymentDBData,
    ) -> None:
        with patch(f"{ROUTE_MODULE}.get_payment_by_id", new=AsyncMock(return_value=sample_payment)) as get_mock:
            resp = await test_client.get(f"/api/v1/payments/{sample_payment.payment_id}", headers=api_key_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["payment_id"] == sample_payment.payment_id
        assert data["amount"] == 199.99
        assert data["currency"] == "RUB"
        assert data["status"] == "pending"
        assert data["metadata"] == {"order_id": 42}
        assert data["processed_at"] is None
        get_mock.assert_called_once()

    async def test_get_payment_not_found(self, test_client: AsyncClient, api_key_headers: dict) -> None:
        with patch(f"{ROUTE_MODULE}.get_payment_by_id", new=AsyncMock(return_value=None)):
            resp = await test_client.get("/api/v1/payments/does-not-exist", headers=api_key_headers)

        assert resp.status_code == HTTP_ERRORS["payment_not_found"].status_code
        assert resp.json()["detail"] == HTTP_ERRORS["payment_not_found"].detail

    async def test_get_payment_without_api_key(self, test_client: AsyncClient) -> None:
        resp = await test_client.get("/api/v1/payments/some-id")
        assert resp.status_code == 422

    async def test_get_payment_with_wrong_api_key(self, test_client: AsyncClient) -> None:
        resp = await test_client.get("/api/v1/payments/some-id", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == HTTP_ERRORS["invalid_api_key"].status_code
