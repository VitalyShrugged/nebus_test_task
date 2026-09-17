import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.fastapi_server.modules.dependences.db_dependence import DBSessionProject
from app.modules.db.postgres.clients import pg_clients
from app.modules.db.postgres.functions.project.outbox import create_outbox_event
from app.modules.db.postgres.functions.project.payments import (
    create_payment,
    get_payment_by_id,
    get_payment_by_idempotency_key,
)
from app.fastapi_server.routes.project.openapi_docs.payments import CREATE_PAYMENT, GET_PAYMENT
from app.modules.project.auth.api_key import verify_api_key
from app.modules.project.http_errors import HTTP_ERRORS
from app.modules.project.schemas.api.payments import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentResponse,
)


router = APIRouter(tags=["payments"], prefix="/payments", dependencies=[Depends(verify_api_key)])


@router.post(
    "",
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    description=CREATE_PAYMENT,
    summary="Create new payment",
)
async def create_payment_handler(
        payment_data: PaymentCreateRequest,
        project_db_session: DBSessionProject,
        idempotency_key: str = Header(..., alias="Idempotency-Key", description="Ключ идемпотентности."),
) -> PaymentCreateResponse:
    payment_id = str(uuid.uuid4())

    async with pg_clients.project_client.transaction_context(db_session=project_db_session):
        payment = await create_payment(
            payment_id=payment_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            description=payment_data.description,
            metadata=payment_data.metadata,
            idempotency_key=idempotency_key,
            webhook_url=payment_data.webhook_url,
            project_db_session=project_db_session,
        )

        if payment:
            # Outbox pattern: событие пишется в той же транзакции, что и платёж,
            # публикация в RabbitMQ гарантируется отдельным релеем (см. outbox_relay.py)
            await create_outbox_event(
                aggregate_type="payment",
                aggregate_id=payment.payment_id,
                event_type="payments.new",
                payload={
                    "payment_id": payment.payment_id,
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "description": payment.description,
                    "metadata": payment.metadata,
                    "webhook_url": payment.webhook_url,
                    "created_at": payment.created_at.isoformat(),
                },
                project_db_session=project_db_session,
            )

    if not payment:
        # запрос с таким Idempotency-Key уже обрабатывался ранее
        payment = await get_payment_by_idempotency_key(
            idempotency_key=idempotency_key, project_db_session=project_db_session,
        )

    if not payment:
        raise HTTPException(
            status_code=HTTP_ERRORS["payment_create_error"].status_code,
            detail=HTTP_ERRORS["payment_create_error"].detail,
        )

    return PaymentCreateResponse(payment_id=payment.payment_id, status=payment.status, created_at=payment.created_at)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    description=GET_PAYMENT,
    summary="Get payment by id",
)
async def get_payment_handler(
        payment_id: str,
        project_db_session: DBSessionProject,
) -> PaymentResponse:
    payment = await get_payment_by_id(payment_id=payment_id, project_db_session=project_db_session)

    if not payment:
        raise HTTPException(
            status_code=HTTP_ERRORS["payment_not_found"].status_code,
            detail=HTTP_ERRORS["payment_not_found"].detail,
        )

    return PaymentResponse(
        payment_id=payment.payment_id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata,
        status=payment.status,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
