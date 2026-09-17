import signal
import sys

import asyncio

from faststream import FastStream

from app.modules.rabbit.payments import consumer  # noqa: F401  # pyright: ignore[reportUnusedImport]  # регистрирует @broker.subscriber
from app.modules.rabbit.payments.broker import broker
from app.modules.rabbit.payments.topology import declare_payments_topology


faststream_app = FastStream(broker)


@faststream_app.after_startup
async def _declare_topology() -> None:
    await declare_payments_topology(broker)


async def main() -> None:
    await faststream_app.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except SystemExit:
        sys.exit(0)
    except BaseException:
        signal.raise_signal(signal.SIGTERM)
