from dataclasses import dataclass

from starlette import status


@dataclass
class HttpError:
    status_code: int
    error_code: str
    detail: str


HTTP_ERRORS = {
    "invalid_api_key": HttpError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        error_code="auth:invalid_api_key",
        detail="Неверный API-ключ.",
    ),
    "payment_not_found": HttpError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="payment:not_found",
        detail="Платёж не найден.",
    ),
    "payment_create_error": HttpError(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code="payment:create_error",
        detail="Ошибка при создании платежа.",
    ),
}
