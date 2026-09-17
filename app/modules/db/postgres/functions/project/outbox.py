import json
from typing import Any

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.db.postgres.clients import pg_clients
from app.modules.project.schemas.api.outbox import OutboxEventDBData


async def create_outbox_event(
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
        project_db_session: AsyncSession | None = None,
) -> OutboxEventDBData | None:
    async with aiofiles.open("app/modules/db/postgres/sql/project/outbox/create_outbox_event.sql", "r") as f:
        sql_query = await f.read()

    params = {
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "event_type": event_type,
        "payload": json.dumps(payload),
    }

    return await pg_clients.project_client.fetch_one_as(
        sql_query=sql_query,
        model=OutboxEventDBData,
        params=params,
        db_session=project_db_session,
    )


async def get_pending_outbox_events(
        limit: int,
        project_db_session: AsyncSession | None = None,
) -> list[OutboxEventDBData]:
    async with aiofiles.open("app/modules/db/postgres/sql/project/outbox/get_pending_outbox_events.sql", "r") as f:
        sql_query = await f.read()

    return await pg_clients.project_client.fetch_many_as(
        sql_query=sql_query,
        model=OutboxEventDBData,
        params={"limit": limit},
        db_session=project_db_session,
    )


async def mark_outbox_event_published(
        event_id: int,
        project_db_session: AsyncSession | None = None,
) -> None:
    async with aiofiles.open("app/modules/db/postgres/sql/project/outbox/mark_outbox_event_published.sql", "r") as f:
        sql_query = await f.read()

    await pg_clients.project_client.execute(
        sql_query=sql_query,
        params={"id": event_id},
        db_session=project_db_session,
    )


async def mark_outbox_event_failed(
        event_id: int,
        error: str,
        project_db_session: AsyncSession | None = None,
) -> None:
    async with aiofiles.open("app/modules/db/postgres/sql/project/outbox/mark_outbox_event_failed.sql", "r") as f:
        sql_query = await f.read()

    await pg_clients.project_client.execute(
        sql_query=sql_query,
        params={"id": event_id, "last_error": error[:1000]},
        db_session=project_db_session,
    )
