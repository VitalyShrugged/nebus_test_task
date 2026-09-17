from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    """
    Интерфейс подключения к бд
    """

    def __init__(self) -> None:
        super().__init__()
        self._db_project_credentials = self._ProjectDataSettings()  # type: ignore

    class _ProjectDataSettings(BaseSettings):
        """
        PG_PROJECT_DATA_HOST: хост с бд, где хранятся данные по данным конкретного приложения
        PG_PROJECT_DATA_PORT: порт к бд, где хранятся данные по данным конкретного приложения
        PG_PROJECT_DATA_DATABASE: название бд, где хранятся данные по данным конкретного приложения
        PG_PROJECT_DATA_USERNAME: логин пользователя от бд
        PG_PROJECT_DATA_PASSWORD: пароль пользователя от бд
        """
        PG_PROJECT_DATA_HOST: str = Field(...)
        PG_PROJECT_DATA_PORT: int = Field(..., gt=1023, le=65535)
        PG_PROJECT_DATA_DATABASE: str = Field(...)
        PG_PROJECT_DATA_USERNAME: SecretStr = Field(...)
        PG_PROJECT_DATA_PASSWORD: SecretStr = Field(...)
        PG_PROJECT_DATA_POOL_SIZE: int = Field(default=5)
        PG_PROJECT_DATA_MAX_OVERFLOW: int = Field(default=2)
        PG_PROJECT_DATA_POOL_RECYCLE: int = Field(default=1000)
        PG_PROJECT_DATA_POOL_TIMEOUT: int = Field(default=60)

    @property
    def db_project_credentials(self) -> _ProjectDataSettings:
        return self._db_project_credentials
