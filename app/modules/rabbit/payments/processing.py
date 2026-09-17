import asyncio
import random

from settings.settings import settings


async def emulate_payment_processing() -> bool:
    """
    Эмулирует обращение к внешнему платёжному шлюзу: задержка 2-5 сек,
    результат — успех с вероятностью PAYMENT_SUCCESS_RATE.
    """
    credentials = settings.consumer.credentials
    delay = random.uniform(credentials.PAYMENT_PROCESSING_MIN_SECONDS, credentials.PAYMENT_PROCESSING_MAX_SECONDS)
    await asyncio.sleep(delay)
    return random.random() < credentials.PAYMENT_SUCCESS_RATE
