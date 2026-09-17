import typing

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.db.postgres.clients import pg_clients

DBSessionProject = typing.Annotated[AsyncSession, Depends(pg_clients.project_client.get_dbsession_depends)]
