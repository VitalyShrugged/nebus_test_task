from app.modules.infra.logs.setting import logger
from app.modules.rabbit.payments.broker import broker
from app.modules.rabbit.payments.outbox_relay import run_outbox_relay
from app.modules.rabbit.payments.topology import declare_payments_topology


async def start_payments_rabbit() -> None:
    try:
        await broker.connect()
        await declare_payments_topology(broker)
        await run_outbox_relay()
    except Exception as e:
        logger.exception(f"start_payments_rabbit failed: {e}")
