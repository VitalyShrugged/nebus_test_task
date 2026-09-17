from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr


class ProjectSettings(BaseSettings):
    """
    Интерфейс данных для работы конкретно этого приложения
    """

    def __init__(self) -> None:
        super().__init__()
        self._credentials = self._ProjectSettings()  # type: ignore

    class _ProjectSettings(BaseSettings):
        """
        API_KEY: статический ключ, обязателен в заголовке X-API-Key для всех эндпоинтов API
        """
        API_KEY: SecretStr = Field(...)

    @property
    def credentials(self) -> _ProjectSettings:
        return self._credentials
