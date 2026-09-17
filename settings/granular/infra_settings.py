from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class InfraSettings(BaseSettings):
    """
    Интерфейс общих данных, которые по умолчанию будут проброшены в любое приложение для его идентификации и работы
    """

    def __init__(self) -> None:
        super().__init__()
        self._credentials = self._InfraSettings()  # type: ignore

    class _InfraSettings(BaseSettings):
        """
        APPLICATION_NAME: Название приложения. Это название будет применено в логах и алертах
        PRODUCTION (Optional): Код запущен на кластере, или локально. По умолчанию принимает значение True
        """
        LOG_LEVEL: Literal["INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
        APPLICATION_NAME: str = Field(...)
        PRODUCTION: bool = Field(default=True)

    @property
    def credentials(self) -> _InfraSettings:
        return self._credentials
