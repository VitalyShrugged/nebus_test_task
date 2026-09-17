import logging
import signal

from pydantic import ValidationError
from settings.granular.consumer_settings import ConsumerSettings
from settings.granular.db_settings import DBSettings
from settings.granular.infra_settings import InfraSettings
from settings.granular.project_settings import ProjectSettings
from settings.granular.rabbit_settings import RabbitSettings


class MainSettings:
    """
    Общий интерфейс всех настроек
    """
    __is_init = False

    def __new__(cls, *args, **kwargs) -> "MainSettings":
        if not cls.__is_init:
            cls.__is_init = True
            return object.__new__(cls)
        raise Exception("Settings cannot be instantiated twice")

    def __init__(self) -> None:
        self.__project_settings = ProjectSettings()
        self.__infra_settings = InfraSettings()
        self.__db_settings = DBSettings()
        self.__rabbit_settings = RabbitSettings()
        self.__consumer_settings = ConsumerSettings()

    @property
    def db(self) -> DBSettings:
        return self.__db_settings

    @property
    def infra(self) -> InfraSettings:
        return self.__infra_settings

    @property
    def project(self) -> ProjectSettings:
        return self.__project_settings

    @property
    def rabbit(self) -> RabbitSettings:
        return self.__rabbit_settings

    @property
    def consumer(self) -> ConsumerSettings:
        return self.__consumer_settings


try:
    settings = MainSettings()
except ValidationError as e:
    errors = [{'type': x['type'], 'loc': x['loc'], 'msg': x['msg']} for x in e.errors()]
    logging.error(f"An error occurred while initializing environment variables: {errors}")
    signal.raise_signal(signal.SIGTERM)
