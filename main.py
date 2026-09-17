import signal
import sys

import asyncio

from app.modules.infra.handler.handler_executor import handler_executor
from app.modules.project.get_fastapi_server import get_server


async def main() -> None:
    fastapi_server = get_server()
    functions = [fastapi_server.run]
    await handler_executor(functions=functions)

    while True:
        await asyncio.sleep(60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except SystemExit:
        sys.exit(0)
    except BaseException:
        signal.raise_signal(signal.SIGTERM)
