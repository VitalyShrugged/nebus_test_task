import asyncio

from app.modules.db.postgres.clients import pg_clients
from app.modules.db.postgres.functions.project.outbox import (
    get_pending_outbox_events,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)
from app.modules.infra.logs.setting import logger
from app.modules.project.schemas.api.outbox import OutboxEventDBData
from app.modules.rabbit.payments.broker import broker
from app.modules.rabbit.payments.topology import PAYMENTS_EXCHANGE
from settings.settings import settings


async def _publish_event(event: OutboxEventDBData) -> None:
    message = {
        "event_id": event.id,
        "event_type": event.event_type,
        "aggregate_id": event.aggregate_id,
        "data": event.payload,
        "attempt": 0,
    }
    await broker.publish(
        message,
        exchange=PAYMENTS_EXCHANGE,
        routing_key=event.event_type,
        persist=True,
    )


async def _process_pending_batch() -> None:
    async with pg_clients.project_client.async_session() as db_session:
        async with pg_clients.project_client.transaction_context(db_session=db_session):
            events = await get_pending_outbox_events(
                limit=settings.rabbit.credentials.OUTBOX_RELAY_BATCH_SIZE, project_db_session=db_session,
            )
            for event in events:
                try:
                    await _publish_event(event=event)
                except Exception as e:
                    logger.error(f"Failed to publish outbox event {event.id}: {e}")
                    await mark_outbox_event_failed(event_id=event.id, error=str(e), project_db_session=db_session)
                else:
                    await mark_outbox_event_published(event_id=event.id, project_db_session=db_session)


async def run_outbox_relay() -> None:
    """
    Бесконечно опрашивает outbox на предмет неотправленных событий и публикует их в RabbitMQ.
    Ошибки публикации не приводят к остановке релея — событие останется status='pending'
    (с приростом attempts и текстом ошибки) и будет подхвачено на следующей итерации.
    """
    while True:
        try:
            await _process_pending_batch()
        except Exception as e:
            logger.exception(f"Outbox relay iteration failed: {e}")
        await asyncio.sleep(settings.rabbit.credentials.OUTBOX_RELAY_POLL_INTERVAL_SECONDS)
