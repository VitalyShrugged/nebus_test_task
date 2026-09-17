import logging

from app.modules.db.postgres.connector.async_connector import PostgresGateway
from settings.settings import settings


class PGClients:
    _project_client = PostgresGateway(
        host=settings.db.db_project_credentials.PG_PROJECT_DATA_HOST,
        port=settings.db.db_project_credentials.PG_PROJECT_DATA_PORT,
        database=settings.db.db_project_credentials.PG_PROJECT_DATA_DATABASE,
        username=settings.db.db_project_credentials.PG_PROJECT_DATA_USERNAME.get_secret_value(),
        password=settings.db.db_project_credentials.PG_PROJECT_DATA_PASSWORD.get_secret_value(),
        pool_size=settings.db.db_project_credentials.PG_PROJECT_DATA_POOL_SIZE,
        max_overflow=settings.db.db_project_credentials.PG_PROJECT_DATA_MAX_OVERFLOW,
        pool_recycle=settings.db.db_project_credentials.PG_PROJECT_DATA_POOL_RECYCLE,
        pool_timeout=settings.db.db_project_credentials.PG_PROJECT_DATA_POOL_TIMEOUT
    )
    logging.info("Initialized PG Project Data Client")

    @property
    def project_client(self) -> PostgresGateway:
        return self._project_client


pg_clients = PGClients()
