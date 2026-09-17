import logging
import typing

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Lifespan


from app.modules.infra.logs.setting import log_config
from settings.settings import settings


class AppServer:
    """
    Собирает FastAPI-приложение и запускает его через uvicorn.
    """

    _active_bindings: typing.ClassVar[set[str]] = set()

    def __init__(
            self,
            application_name: str = settings.infra.credentials.APPLICATION_NAME,
            host: str = "0.0.0.0",
            port: int = 8000,
            openapi_url: str = "/openapi.json",
            lifespan: Lifespan[FastAPI] | None = None,
    ) -> None:
        if host == "127.0.0.1":
            host = "0.0.0.0"

        self._bind_key = f"{host}:{port}"
        self._register_binding()

        self._application_name = application_name
        self._host = host
        self._port = port
        self._openapi_url = openapi_url
        self._lifespan = lifespan
        self._application = self._build_app()

    def _register_binding(self) -> None:
        """Не даёт создать второй сервер на том же host:port в рамках одного процесса."""
        if self._bind_key in self._active_bindings:
            raise RuntimeError(f"Server already running at {self._bind_key}")
        self._active_bindings.add(self._bind_key)

    def _release_binding(self) -> None:
        self._active_bindings.discard(self._bind_key)

    def run(self) -> None:
        try:
            config = uvicorn.Config(
                app=self._application, host=self._host, port=self._port,
                log_level=settings.infra.credentials.LOG_LEVEL.lower(), log_config=log_config,
            )
            uvicorn.Server(config=config).run()
        except Exception as e:
            logging.exception(f"AppServer.run failed: {e}")
        finally:
            self._release_binding()

    def _build_app(self) -> FastAPI:
        application = FastAPI(
            title=self._application_name,
            debug=not settings.infra.credentials.PRODUCTION,
            openapi_url=self._openapi_url,
            lifespan=self._lifespan,
        )

        application.add_middleware(
            CORSMiddleware,  # type: ignore
            allow_origins=["*"],
            allow_methods=["*"],  # Разрешает все методы HTTP
            allow_headers=["*"],  # Разрешает все заголовки
        )

        return application

    def include_router(self, router: APIRouter, prefix: str = "") -> None:
        self._application.include_router(router, prefix=prefix)
