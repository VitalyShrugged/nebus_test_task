from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class RabbitSettings(BaseSettings):
    """
    Интерфейс подключения к RabbitMQ
    """

    def __init__(self) -> None:
        super().__init__()
        self._credentials = self._RabbitSettings()  # type: ignore

    class _RabbitSettings(BaseSettings):
        """
        RABBIT_HOST: host, где развернут RabbitMQ
        RABBIT_PORT_SERVER (Optional): Порт, на котором развернут RabbitMQ Server. По умолчанию 5672
        RABBIT_USER: Логин пользователя
        RABBIT_PASSWORD: Пароль пользователя
        OUTBOX_RELAY_BATCH_SIZE (Optional): Сколько событий outbox забирать за одну итерацию релея
        OUTBOX_RELAY_POLL_INTERVAL_SECONDS (Optional): Пауза между итерациями релея, в секундах
        """
        RABBIT_HOST: str = Field(...)
        RABBIT_PORT_SERVER: int = Field(gt=1023, le=65535, default=5672)
        RABBIT_USER: SecretStr = Field(...)
        RABBIT_PASSWORD: SecretStr = Field(...)
        OUTBOX_RELAY_BATCH_SIZE: int = Field(default=20, gt=0)
        OUTBOX_RELAY_POLL_INTERVAL_SECONDS: float = Field(default=2.0, gt=0)

    @property
    def credentials(self) -> _RabbitSettings:
        return self._credentials
