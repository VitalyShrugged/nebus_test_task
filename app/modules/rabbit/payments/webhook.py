import asyncio

import aiohttp

from app.modules.infra.logs.setting import logger
from app.modules.project.schemas.api.payments import PaymentDBData
from settings.settings import settings


async def send_webhook_notification(payment: PaymentDBData) -> None:
    """
    Отправляет клиенту уведомление о результате обработки платежа.
    Ошибки доставки webhook не влияют на статус платежа (он уже сохранён в БД) —
    здесь только попытки повторной отправки с экспоненциальной задержкой.
    """
    credentials = settings.consumer.credentials
    body = {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }
    timeout = aiohttp.ClientTimeout(total=credentials.WEBHOOK_TIMEOUT_SECONDS)

    last_error: Exception | None = None
    for attempt in range(credentials.WEBHOOK_MAX_ATTEMPTS):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(payment.webhook_url, json=body) as response:
                    response.raise_for_status()
            return
        except Exception as e:
            last_error = e
            logger.warning(
                f"Webhook attempt {attempt + 1}/{credentials.WEBHOOK_MAX_ATTEMPTS} failed "
                f"for payment {payment.payment_id}: {e}"
            )
            if attempt + 1 < credentials.WEBHOOK_MAX_ATTEMPTS:
                await asyncio.sleep(credentials.WEBHOOK_RETRY_BASE_DELAY_SECONDS * (2 ** attempt))

    logger.error(f"Webhook delivery permanently failed for payment {payment.payment_id}: {last_error}")
