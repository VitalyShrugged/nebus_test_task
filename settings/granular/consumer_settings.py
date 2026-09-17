from pydantic import Field
from pydantic_settings import BaseSettings


class ConsumerSettings(BaseSettings):
    """
    Настройки consumer'а платежей: эмуляция обработки, message-level retry и webhook.
    """

    def __init__(self) -> None:
        super().__init__()
        self._credentials = self._ConsumerSettings()  # type: ignore

    class _ConsumerSettings(BaseSettings):
        """
        PAYMENT_PROCESSING_MIN_SECONDS (Optional): минимальная задержка эмуляции обработки платежа
        PAYMENT_PROCESSING_MAX_SECONDS (Optional): максимальная задержка эмуляции обработки платежа
        PAYMENT_SUCCESS_RATE (Optional): доля успешных обработок, от 0 до 1
        MESSAGE_MAX_ATTEMPTS (Optional): сколько раз пытаться обработать сообщение, прежде чем уйти в DLQ
        MESSAGE_RETRY_BASE_DELAY_SECONDS (Optional): база экспоненциальной задержки между попытками обработки
        WEBHOOK_MAX_ATTEMPTS (Optional): сколько раз пытаться отправить webhook-уведомление
        WEBHOOK_RETRY_BASE_DELAY_SECONDS (Optional): база экспоненциальной задержки между попытками webhook
        WEBHOOK_TIMEOUT_SECONDS (Optional): таймаут HTTP-запроса на webhook
        """
        PAYMENT_PROCESSING_MIN_SECONDS: float = Field(default=2.0, gt=0)
        PAYMENT_PROCESSING_MAX_SECONDS: float = Field(default=5.0, gt=0)
        PAYMENT_SUCCESS_RATE: float = Field(default=0.9, ge=0, le=1)
        MESSAGE_MAX_ATTEMPTS: int = Field(default=3, gt=0)
        MESSAGE_RETRY_BASE_DELAY_SECONDS: float = Field(default=5.0, gt=0)
        WEBHOOK_MAX_ATTEMPTS: int = Field(default=3, gt=0)
        WEBHOOK_RETRY_BASE_DELAY_SECONDS: float = Field(default=1.0, gt=0)
        WEBHOOK_TIMEOUT_SECONDS: float = Field(default=5.0, gt=0)

    @property
    def credentials(self) -> _ConsumerSettings:
        return self._credentials
