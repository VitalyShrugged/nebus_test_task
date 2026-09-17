"""
Патчим PostgresGateway до того, как любой тестовый модуль успеет импортировать
app.modules.db.postgres.clients — иначе PGClients() при импорте попытается
установить настоящее соединение с Postgres.
"""
from unittest.mock import patch

_postgres_gateway_patcher = patch(
    "app.modules.db.postgres.connector.async_connector.PostgresGateway", autospec=True,
)
_postgres_gateway_patcher.start()
