from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.modules.project.schemas.api.payments import PaymentDBData, PaymentStatus
from app.modules.rabbit.payments.consumer import handle_payment_new

MODULE = "app.modules.rabbit.payments.consumer"


def _payment(status: PaymentStatus = "pending") -> PaymentDBData:
    return PaymentDBData(
        payment_id="payment-1",
        amount=Decimal("10.00"),
        currency="RUB",
        status=status,
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def message() -> MagicMock:
    msg = MagicMock()
    msg.ack = AsyncMock()
    msg.nack = AsyncMock()
    return msg


class TestHandlePaymentNewSuccess:
    async def test_marks_payment_succeeded_and_sends_webhook(self, message: MagicMock) -> None:
        pending_payment = _payment(status="pending")
        succeeded_payment = _payment(status="succeeded")

        with (
            patch(f"{MODULE}.get_payment_by_id", new=AsyncMock(return_value=pending_payment)),
            patch(f"{MODULE}.update_payment_status", new=AsyncMock(return_value=succeeded_payment)) as update_mock,
            patch(f"{MODULE}.emulate_payment_processing", new=AsyncMock(return_value=True)),
            patch(f"{MODULE}.send_webhook_notification", new=AsyncMock()) as webhook_mock,
            patch(f"{MODULE}.broker.publish", new=AsyncMock()) as publish_mock,
        ):
            await handle_payment_new(body={"aggregate_id": "payment-1", "attempt": 0}, message=message)

        update_mock.assert_called_once_with(payment_id="payment-1", status="succeeded")
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        webhook_mock.assert_called_once_with(payment=succeeded_payment)
        publish_mock.assert_not_called()


class TestHandlePaymentNewRetry:
    @pytest.mark.parametrize("attempt, expected_delay", [(0, 5.0), (1, 10.0)])
    async def test_schedules_retry_with_exponential_delay(
            self, message: MagicMock, attempt: int, expected_delay: float,
    ) -> None:
        pending_payment = _payment(status="pending")

        with (
            patch(f"{MODULE}.get_payment_by_id", new=AsyncMock(return_value=pending_payment)),
            patch(f"{MODULE}.update_payment_status", new=AsyncMock()) as update_mock,
            patch(f"{MODULE}.emulate_payment_processing", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}.send_webhook_notification", new=AsyncMock()) as webhook_mock,
            patch(f"{MODULE}.broker.publish", new=AsyncMock()) as publish_mock,
        ):
            await handle_payment_new(body={"aggregate_id": "payment-1", "attempt": attempt}, message=message)

        publish_mock.assert_called_once_with(
            {"aggregate_id": "payment-1", "attempt": attempt + 1},
            exchange=ANY,
            routing_key="payments.new.retry",
            expiration=expected_delay,
            persist=True,
        )
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        update_mock.assert_not_called()
        webhook_mock.assert_not_called()


class TestHandlePaymentNewDeadLetter:
    async def test_marks_payment_failed_and_nacks_after_max_attempts(self, message: MagicMock) -> None:
        pending_payment = _payment(status="pending")
        failed_payment = _payment(status="failed")

        with (
            patch(f"{MODULE}.get_payment_by_id", new=AsyncMock(return_value=pending_payment)),
            patch(f"{MODULE}.update_payment_status", new=AsyncMock(return_value=failed_payment)) as update_mock,
            patch(f"{MODULE}.emulate_payment_processing", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}.send_webhook_notification", new=AsyncMock()) as webhook_mock,
            patch(f"{MODULE}.broker.publish", new=AsyncMock()) as publish_mock,
        ):
            # attempt=2 -> третья (последняя) попытка при MESSAGE_MAX_ATTEMPTS=3
            await handle_payment_new(body={"aggregate_id": "payment-1", "attempt": 2}, message=message)

        update_mock.assert_called_once_with(payment_id="payment-1", status="failed")
        message.nack.assert_called_once_with(requeue=False)
        message.ack.assert_not_called()
        publish_mock.assert_not_called()
        webhook_mock.assert_called_once_with(payment=failed_payment)


class TestHandlePaymentNewEdgeCases:
    async def test_drops_message_without_aggregate_id(self, message: MagicMock) -> None:
        with patch(f"{MODULE}.get_payment_by_id", new=AsyncMock()) as get_mock:
            await handle_payment_new(body={"attempt": 0}, message=message)

        get_mock.assert_not_called()
        message.ack.assert_called_once()

    async def test_drops_message_for_unknown_payment(self, message: MagicMock) -> None:
        with (
            patch(f"{MODULE}.get_payment_by_id", new=AsyncMock(return_value=None)),
            patch(f"{MODULE}.emulate_payment_processing", new=AsyncMock()) as emulate_mock,
        ):
            await handle_payment_new(body={"aggregate_id": "unknown"}, message=message)

        emulate_mock.assert_not_called()
        message.ack.assert_called_once()

    async def test_skips_already_processed_payment(self, message: MagicMock) -> None:
        already_succeeded = _payment(status="succeeded")

        with (
            patch(f"{MODULE}.get_payment_by_id", new=AsyncMock(return_value=already_succeeded)),
            patch(f"{MODULE}.emulate_payment_processing", new=AsyncMock()) as emulate_mock,
        ):
            await handle_payment_new(body={"aggregate_id": "payment-1"}, message=message)

        emulate_mock.assert_not_called()
        message.ack.assert_called_once()
