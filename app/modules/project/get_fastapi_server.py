from app.fastapi_server.fastapi_server import AppServer
from app.fastapi_server.modules.lifespan.lifespan import lifespan

from app.fastapi_server.routes.project.payments import router as payments


def get_server() -> AppServer:

    app_server = AppServer(lifespan=lifespan)

    app_server.include_router(router=payments, prefix="/api/v1")

    return app_server
