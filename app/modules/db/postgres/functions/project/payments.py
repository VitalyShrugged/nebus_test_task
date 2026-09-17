import json
from decimal import Decimal
from typing import Any

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.db.postgres.clients import pg_clients
from app.modules.project.schemas.api.payments import PaymentDBData


async def create_payment(
        payment_id: str,
        amount: Decimal,
        currency: str,
        description: str | None,
        metadata: dict[str, Any] | None,
        idempotency_key: str,
        webhook_url: str,
        project_db_session: AsyncSession | None = None,
) -> PaymentDBData | None:
    async with aiofiles.open("app/modules/db/postgres/sql/project/payments/create_payment.sql", "r") as f:
        sql_query = await f.read()

    params = {
        "payment_id": payment_id,
        "amount": amount,
        "currency": currency,
        "description": description,
        "metadata": json.dumps(metadata) if metadata is not None else None,
        "status": "pending",
        "idempotency_key": idempotency_key,
        "webhook_url": webhook_url,
    }

    return await pg_clients.project_client.fetch_one_as(
        sql_query=sql_query,
        model=PaymentDBData,
        params=params,
        db_session=project_db_session,
    )


async def get_payment_by_id(
        payment_id: str,
        project_db_session: AsyncSession | None = None,
) -> PaymentDBData | None:
    async with aiofiles.open("app/modules/db/postgres/sql/project/payments/get_payment_by_id.sql", "r") as f:
        sql_query = await f.read()

    return await pg_clients.project_client.fetch_one_as(
        sql_query=sql_query,
        model=PaymentDBData,
        params={"payment_id": payment_id},
        db_session=project_db_session,
    )


async def get_payment_by_idempotency_key(
        idempotency_key: str,
        project_db_session: AsyncSession | None = None,
) -> PaymentDBData | None:
    async with aiofiles.open(
            "app/modules/db/postgres/sql/project/payments/get_payment_by_idempotency_key.sql", "r"
    ) as f:
        sql_query = await f.read()

    return await pg_clients.project_client.fetch_one_as(
        sql_query=sql_query,
        model=PaymentDBData,
        params={"idempotency_key": idempotency_key},
        db_session=project_db_session,
    )


async def update_payment_status(
        payment_id: str,
        status: str,
        project_db_session: AsyncSession | None = None,
) -> PaymentDBData | None:
    async with aiofiles.open("app/modules/db/postgres/sql/project/payments/update_payment_status.sql", "r") as f:
        sql_query = await f.read()

    return await pg_clients.project_client.fetch_one_as(
        sql_query=sql_query,
        model=PaymentDBData,
        params={"payment_id": payment_id, "status": status},
        db_session=project_db_session,
    )
