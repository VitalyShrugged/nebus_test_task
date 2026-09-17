from faststream.middlewares.acknowledgement.config import AckPolicy
from faststream.rabbit import RabbitMessage

from app.modules.db.postgres.functions.project.payments import get_payment_by_id, update_payment_status
from app.modules.infra.logs.setting import logger
from app.modules.rabbit.payments.broker import broker
from app.modules.rabbit.payments.processing import emulate_payment_processing
from app.modules.rabbit.payments.topology import PAYMENTS_EXCHANGE, PAYMENTS_NEW_QUEUE
from app.modules.rabbit.payments.webhook import send_webhook_notification
from settings.settings import settings


@broker.subscriber(PAYMENTS_NEW_QUEUE, PAYMENTS_EXCHANGE, ack_policy=AckPolicy.MANUAL)
async def handle_payment_new(body: dict, message: RabbitMessage) -> None:
    payment_id = body.get("aggregate_id")
    attempt = body.get("attempt", 0)

    if not payment_id:
        logger.error(f"payments.new message without aggregate_id, dropping: {body}")
        await message.ack()
        return

    payment = await get_payment_by_id(payment_id=payment_id)
    if payment is None:
        logger.error(f"payments.new message references unknown payment_id={payment_id}, dropping")
        await message.ack()
        return

    if payment.status != "pending":
        # Уже обработан (повторная доставка сообщения) — идемпотентно пропускаем.
        await message.ack()
        return

    credentials = settings.consumer.credentials
    succeeded = await emulate_payment_processing()

    if succeeded:
        updated = await update_payment_status(payment_id=payment_id, status="succeeded")
        await message.ack()
        logger.info(f"Payment {payment_id} processed successfully")
        if updated:
            await send_webhook_notification(payment=updated)
        return

    if attempt + 1 < credentials.MESSAGE_MAX_ATTEMPTS:
        delay_seconds = credentials.MESSAGE_RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
        await broker.publish(
            {**body, "attempt": attempt + 1},
            exchange=PAYMENTS_EXCHANGE,
            routing_key="payments.new.retry",
            expiration=delay_seconds,
            persist=True,
        )
        await message.ack()
        logger.warning(
            f"Payment {payment_id} processing failed "
            f"(attempt {attempt + 1}/{credentials.MESSAGE_MAX_ATTEMPTS}), retry in {delay_seconds:.1f}s"
        )
        return

    # Попытки исчерпаны: помечаем платёж проваленным и отдаём сообщение под DLQ
    # (payments.new настроена с x-dead-letter-exchange -> payments.new.dlq).
    updated = await update_payment_status(payment_id=payment_id, status="failed")
    await message.nack(requeue=False)
    logger.error(f"Payment {payment_id} failed permanently after {credentials.MESSAGE_MAX_ATTEMPTS} attempts")
    if updated:
        await send_webhook_notification(payment=updated)
