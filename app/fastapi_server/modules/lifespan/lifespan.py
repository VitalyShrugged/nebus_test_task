from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.modules.infra.handler.handler_executor import handler_executor

from app.modules.rabbit.payments.start_payments_rabbit import start_payments_rabbit


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    functions = [start_payments_rabbit]
    await handler_executor(functions=functions)
    yield
