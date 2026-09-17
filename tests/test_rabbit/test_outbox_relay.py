from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, patch

from app.modules.project.schemas.api.outbox import OutboxEventDBData
from app.modules.rabbit.payments.outbox_relay import _process_pending_batch

MODULE = "app.modules.rabbit.payments.outbox_relay"


def _event(event_id: int) -> OutboxEventDBData:
    return OutboxEventDBData(
        id=event_id,
        aggregate_type="payment",
        aggregate_id=f"payment-{event_id}",
        event_type="payments.new",
        payload={"payment_id": f"payment-{event_id}"},
        status="pending",
        attempts=0,
        created_at=datetime.now(timezone.utc),
    )


class TestProcessPendingBatch:
    async def test_publishes_and_marks_all_events_when_successful(self) -> None:
        events = [_event(1), _event(2)]

        with (
            patch(f"{MODULE}.get_pending_outbox_events", new=AsyncMock(return_value=events)),
            patch(f"{MODULE}.broker.publish", new=AsyncMock()) as publish_mock,
            patch(f"{MODULE}.mark_outbox_event_published", new=AsyncMock()) as published_mock,
            patch(f"{MODULE}.mark_outbox_event_failed", new=AsyncMock()) as failed_mock,
        ):
            await _process_pending_batch()

        assert publish_mock.call_count == 2
        published_mock.assert_any_call(event_id=1, project_db_session=ANY)
        published_mock.assert_any_call(event_id=2, project_db_session=ANY)
        failed_mock.assert_not_called()

    async def test_marks_event_failed_when_publish_raises(self) -> None:
        events = [_event(1)]

        with (
            patch(f"{MODULE}.get_pending_outbox_events", new=AsyncMock(return_value=events)),
            patch(f"{MODULE}.broker.publish", new=AsyncMock(side_effect=Exception("broker unavailable"))),
            patch(f"{MODULE}.mark_outbox_event_published", new=AsyncMock()) as published_mock,
            patch(f"{MODULE}.mark_outbox_event_failed", new=AsyncMock()) as failed_mock,
        ):
            await _process_pending_batch()

        failed_mock.assert_called_once_with(event_id=1, error="broker unavailable", project_db_session=ANY)
        published_mock.assert_not_called()

    async def test_mixed_batch_marks_each_event_independently(self) -> None:
        events = [_event(1), _event(2)]

        async def publish_side_effect(message: dict, **kwargs: object) -> None:
            if message["event_id"] == 2:
                raise Exception("boom")

        with (
            patch(f"{MODULE}.get_pending_outbox_events", new=AsyncMock(return_value=events)),
            patch(f"{MODULE}.broker.publish", new=AsyncMock(side_effect=publish_side_effect)),
            patch(f"{MODULE}.mark_outbox_event_published", new=AsyncMock()) as published_mock,
            patch(f"{MODULE}.mark_outbox_event_failed", new=AsyncMock()) as failed_mock,
        ):
            await _process_pending_batch()

        published_mock.assert_called_once_with(event_id=1, project_db_session=ANY)
        failed_mock.assert_called_once_with(event_id=2, error="boom", project_db_session=ANY)
