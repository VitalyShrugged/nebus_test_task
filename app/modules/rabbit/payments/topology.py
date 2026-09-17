"""
Топология очередей для событий платежей.

Один direct-exchange "payments" и три очереди, связанные между собой через
dead-lettering (без плагинов задержки):

  payments.new         — основная очередь, которую читает consumer.
                         При окончательном отказе (nack без requeue после
                         исчерпания попыток) сообщение уходит в payments.new.dlq.

  payments.new.retry   — "очередь-парковка": ни один consumer её не читает.
                         Сообщение публикуется сюда с индивидуальным TTL
                         (параметр `expiration` при публикации), и после
                         истечения TTL RabbitMQ сама пересылает его обратно
                         в payments.new — так получается задержка перед
                         повторной попыткой без сторонних плагинов.

  payments.new.dlq     — Dead Letter Queue для сообщений, не обработанных
                         после исчерпания попыток.
"""

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

PAYMENTS_EXCHANGE = RabbitExchange(name="payments", type=ExchangeType.DIRECT, durable=True)

PAYMENTS_NEW_QUEUE = RabbitQueue(
    name="payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": PAYMENTS_EXCHANGE.name,
        "x-dead-letter-routing-key": "payments.new.dlq",
    },
)

PAYMENTS_RETRY_QUEUE = RabbitQueue(
    name="payments.new.retry",
    durable=True,
    routing_key="payments.new.retry",
    arguments={
        "x-dead-letter-exchange": PAYMENTS_EXCHANGE.name,
        "x-dead-letter-routing-key": "payments.new",
    },
)

PAYMENTS_DLQ_QUEUE = RabbitQueue(
    name="payments.new.dlq",
    durable=True,
    routing_key="payments.new.dlq",
)

PAYMENTS_QUEUES = (PAYMENTS_NEW_QUEUE, PAYMENTS_RETRY_QUEUE, PAYMENTS_DLQ_QUEUE)


async def declare_payments_topology(broker: RabbitBroker) -> None:
    exchange = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    for queue in PAYMENTS_QUEUES:
        queue_obj = await broker.declare_queue(queue)
        await queue_obj.bind(exchange, routing_key=queue.routing())
