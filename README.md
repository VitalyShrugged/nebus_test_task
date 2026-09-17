# Nebus test task - Payments Service

Асинхронный микросервис процессинга платежей: принимает запрос на оплату, эмулирует
обработку через внешний платёжный шлюз и уведомляет клиента о результате через webhook.

## Архитектура

```
                 POST /api/v1/payments
                        │
                        ▼
                 ┌─────────────┐        одна транзакция БД
                 │     API     │───────────────────────────┐
                 └─────────────┘                            │
                        │                                   ▼
                        │                          ┌──────────────────┐
                        │ фоновый релей            │  payments table  │
                        │ (внутри API-процесса)    │  outbox table    │
                        ▼                          └──────────────────┘
                 exchange "payments"
                        │  payments.new
                        ▼
                 ┌─────────────┐   успех   ┌──────────────────┐
                 │  Consumer   │──────────▶│ status=succeeded │──▶ webhook
                 └─────────────┘           └──────────────────┘
                        │  ошибка (< 3 попыток)
                        ▼
              payments.new.retry (TTL = экспоненциальная задержка)
                        │  TTL истёк → назад в payments.new
                        ▼
                (повторная обработка, до 3 попыток суммарно)
                        │  3-я попытка неудачна
                        ▼
                  payments.new.dlq (Dead Letter Queue)
```

- **Outbox pattern**: событие `payments.new` пишется в таблицу `outbox` в той же
  транзакции, что и сам платёж. Отдельный фоновый релей (часть API-процесса) опрашивает
  `outbox` и публикует неотправленные события в RabbitMQ — доставка гарантирована даже
  если в момент создания платежа брокер недоступен.
- **Retry с экспоненциальной задержкой**: при ошибке обработки сообщение публикуется в
  очередь-парковку `payments.new.retry` с индивидуальным TTL (`MESSAGE_RETRY_BASE_DELAY_SECONDS * 2^attempt`).
  По истечении TTL RabbitMQ сама возвращает сообщение в `payments.new` — без плагинов задержки.
- **Dead Letter Queue**: после `MESSAGE_MAX_ATTEMPTS` (по умолчанию 3) неудачных попыток
  сообщение уходит в `payments.new.dlq`, а платёж помечается `failed`.
- **Idempotency-Key**: обязательный заголовок при создании платежа; повторный запрос с тем
  же ключом не создаёт новую запись, а возвращает уже существующий платёж.

## Стек

FastAPI + Pydantic v2 · SQLAlchemy 2.0 (async) + Alembic · PostgreSQL · RabbitMQ (FastStream) · Docker Compose

## Быстрый старт (Docker)

Понадобятся Docker и Docker Compose (`docker compose version`).

```bash
git clone <repo-url>
cd nebus_test_task
cp .env.docker.example .env.docker
docker compose up --build
```

`.env.docker` — конфигурация специально для Docker-окружения (хосты `postgres`/`rabbitmq`,
т.е. имена сервисов из `docker-compose.yml`). Она отдельная от `.env`, который нужен для
запуска без Docker (там хосты `127.0.0.1`) — эти два сценария используют разные хосты для
БД и брокера, поэтому не пытаемся впихнуть оба варианта в один файл.

Это поднимет 5 сервисов:

| Сервис     | Что делает                                                             |
|------------|-------------------------------------------------------------------------|
| `postgres` | БД, порт `5432`                                                        |
| `rabbitmq` | брокер, порт `5672`, management UI на `15672`                          |
| `migrate`  | одноразово прогоняет `alembic upgrade head` и завершается              |
| `api`      | FastAPI-сервер (порт `8000`) + фоновый outbox-релей                    |
| `consumer` | читает `payments.new`, обрабатывает платежи, шлёт webhook              |

`api` и `consumer` стартуют только после того, как `migrate` успешно отработает, а
`postgres`/`rabbitmq` пройдут healthcheck — руками ничего дожидаться не нужно.

> **Почему `api` и `consumer` — два отдельных процесса** (`main.py` и `consumer.py`),
> а не один: это осознанное архитектурное решение. Во-первых, так
> явно требует ТЗ (п.7 — `docker-compose` с отдельными `api` и `consumer`). Во-вторых,
> это даёт реальные преимущества: если в обработке платежа возникнет проблема (завис
> webhook, консьюмер упал) — API продолжит принимать запросы независимо, и наоборот.
> Плюс так их можно масштабировать по отдельности на уровне Docker/оркестрации —
> например, `docker compose up --scale consumer=3`, чтобы поднять несколько
> consumer'ов под нагрузкой, не трогая `api`.

Проверить, что всё поднялось:

```bash
docker compose ps
docker compose logs -f api consumer
```

Ключ из `.env.docker` (`API_KEY`, по умолчанию `nebus-test_task_123`) нужно передавать в заголовке
`X-API-Key` во всех запросах ниже.

## Использование API

Swagger UI: http://localhost:8000/docs

### Создать платёж

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: nebus-test_task_123" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "amount": "199.99",
    "currency": "RUB",
    "description": "Order #42",
    "metadata": {"order_id": 42},
    "webhook_url": "https://example.com/webhook"
  }'
```

Ответ `202 Accepted`:

```json
{
  "payment_id": "…",
  "status": "pending",
  "created_at": "…"
}
```

### Получить платёж

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> \
  -H "X-API-Key: nebus-test_task_123"
```

```json
{
  "payment_id": "…",
  "amount": 199.99,
  "currency": "RUB",
  "description": "Order #42",
  "metadata": {"order_id": 42},
  "status": "succeeded",
  "webhook_url": "https://example.com/webhook",
  "created_at": "…",
  "processed_at": "…"
}
```

Статус меняется с `pending` на `succeeded`/`failed` асинхронно — обычно в течение
2–5 секунд (эмуляция обработки), при ретраях дольше. Webhook уходит на указанный
`webhook_url` сразу по завершении обработки.

> `https://example.com/webhook` в примерах — просто заглушка для демонстрации формы
> запроса, она не примет webhook по-настоящему (`example.com` отвечает `405` на POST).
> Платёж при этом всё равно корректно обработается — доставка webhook не влияет на
> статус платежа, а лишь ретраится независимо (см. `WEBHOOK_MAX_ATTEMPTS`).

### Понаблюдать за очередями

RabbitMQ management UI: http://localhost:15672 (`guest` / `guest` по умолчанию) —
там видно очереди `payments.new`, `payments.new.retry`, `payments.new.dlq` и их
наполнение в реальном времени.

### Как вручную воспроизвести retry → DLQ

По умолчанию обработка платежа успешна в 90% случаев (`PAYMENT_SUCCESS_RATE`), поэтому
ретраи возникают не всегда. Чтобы гарантированно увидеть полный цикл 2 ретрая → DLQ,
временно заставьте consumer всегда "проваливать" обработку:

**Docker.** Добавьте в `.env.docker`:
```
PAYMENT_SUCCESS_RATE=0
MESSAGE_RETRY_BASE_DELAY_SECONDS=2
```
(вторая переменная — чтобы не ждать дефолтные 5с/10с, а увидеть цикл за секунды) и
пересоздайте контейнер, чтобы он подхватил новые переменные:
```bash
docker compose up -d --force-recreate consumer
```

**Локально:**
```bash
PAYMENT_SUCCESS_RATE=0 MESSAGE_RETRY_BASE_DELAY_SECONDS=2 poetry run python consumer.py
```

Дальше создайте платёж (см. выше) и смотрите:

1. **Логи consumer'а** — три записи подряд:
   ```
   Payment ... processing failed (attempt 1/3), retry in 2.0s
   Payment ... processing failed (attempt 2/3), retry in 4.0s
   Payment ... failed permanently after 3 attempts
   ```
2. **RabbitMQ UI** — сообщение перескакивает `payments.new` → `payments.new.retry` →
   назад в `payments.new` → и в итоге оседает в `payments.new.dlq`.
3. **GET платежа** — статус в итоге `failed`.

Весь цикл занимает ~15–25 секунд (эмуляция обработки 2–5с на попытку + задержки
ретраев). После теста верните `PAYMENT_SUCCESS_RATE`/`MESSAGE_RETRY_BASE_DELAY_SECONDS`
обратно (или просто уберите строки из `.env.docker` — сработают дефолты 0.9 и 5.0) и
пересоздайте consumer ещё раз.

## Локальный запуск без Docker

Нужны Python 3.13+, Poetry, и локально поднятые Postgres/RabbitMQ.

```bash
poetry install --no-root
cp .env_example .env   # PG_PROJECT_DATA_HOST/RABBIT_HOST должны указывать на ваши локальные postgres/rabbitmq
poetry run alembic upgrade head

# в отдельных терминалах
poetry run python main.py
poetry run python consumer.py
```

## Тесты и линтеры

Тестам и линтерам не нужны Postgres/RabbitMQ — вся БД и брокер замоканы (см.
`tests/conftest.py`), тесты изолированные и быстрые.

Дополнительные группы зависимостей (не входят в базовый `poetry install`):
```bash
poetry install --no-root --with tests,pre-commit
```

Тесты:
```bash
pytest . -s -v
```

Линтеры и статическая проверка типов (ruff, pyright, autopep8 и другие хуки — см.
`.pre-commit-config.yaml`):
```bash
pre-commit run --all-files
```

## Переменные окружения

| Переменная | Обязательна | По умолчанию  | Назначение |
|---|---|---------------|---|
| `PG_PROJECT_DATA_HOST/PORT/DATABASE/USERNAME/PASSWORD` | да | —             | подключение к Postgres |
| `RABBIT_HOST/USER/PASSWORD` | да | —             | подключение к RabbitMQ |
| `RABBIT_PORT_SERVER` | нет | `5672`        | порт RabbitMQ |
| `API_KEY` | да | —             | статический ключ для заголовка `X-API-Key` |
| `APPLICATION_NAME` | да | —             | имя приложения (для логов) |
| `LOG_LEVEL` | нет | `INFO`        | уровень логирования |
| `OUTBOX_RELAY_BATCH_SIZE` | нет | `20`          | сколько событий outbox забирать за одну итерацию релея |
| `OUTBOX_RELAY_POLL_INTERVAL_SECONDS` | нет | `2.0`         | пауза между итерациями релея |
| `PAYMENT_PROCESSING_MIN/MAX_SECONDS` | нет | `2.0` / `5.0` | диапазон эмуляции задержки обработки платежа |
| `PAYMENT_SUCCESS_RATE` | нет | `0.9`           | доля успешных обработок (0..1) |
| `MESSAGE_MAX_ATTEMPTS` | нет | `3`           | попыток обработки сообщения перед DLQ |
| `MESSAGE_RETRY_BASE_DELAY_SECONDS` | нет | `5.0`         | база экспоненциальной задержки retry |
| `WEBHOOK_MAX_ATTEMPTS` | нет | `3`           | попыток отправки webhook |
| `WEBHOOK_RETRY_BASE_DELAY_SECONDS` | нет | `1.0`         | база экспоненциальной задержки webhook |
| `WEBHOOK_TIMEOUT_SECONDS` | нет | `5.0`         | таймаут HTTP-запроса на webhook |

Таблица описывает переменные приложения — они одинаковы что для `.env` (локальный запуск),
что для `.env.docker` (Docker), отличаются только значения `PG_PROJECT_DATA_HOST`/`RABBIT_HOST`
(`127.0.0.1` локально, `postgres`/`rabbitmq` в Docker — см. `.env.docker.example`). Сами
сервисы `postgres`/`rabbitmq` в `docker-compose.yml` используют фиксированные dev-креды
(`postgres`/`postgres`, `guest`/`guest`), которые уже соответствуют дефолтам в `.env.docker.example`.

## Миграции

```bash
docker compose run --rm migrate                       # накатить миграции вручную (Docker)
poetry run alembic upgrade head                        # то же самое локально
poetry run alembic revision --autogenerate -m "..."     # создать новую миграцию
poetry run alembic downgrade -1                         # откатить последнюю
```
