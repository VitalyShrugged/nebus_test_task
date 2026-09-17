from urllib.parse import quote

from faststream.rabbit import RabbitBroker

from settings.settings import settings


def _build_amqp_url() -> str:
    credentials = settings.rabbit.credentials
    user = quote(credentials.RABBIT_USER.get_secret_value())
    password = quote(credentials.RABBIT_PASSWORD.get_secret_value())
    return f"amqp://{user}:{password}@{credentials.RABBIT_HOST}:{credentials.RABBIT_PORT_SERVER}/"


broker = RabbitBroker(_build_amqp_url())
