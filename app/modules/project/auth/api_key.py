import hmac

from fastapi import Header, HTTPException

from app.modules.project.http_errors import HTTP_ERRORS
from settings.settings import settings


async def verify_api_key(
        x_api_key: str = Header(..., alias="X-API-Key", description="Статический API-ключ."),
) -> None:
    expected_api_key = settings.project.credentials.API_KEY.get_secret_value()
    if not hmac.compare_digest(x_api_key, expected_api_key):
        raise HTTPException(
            status_code=HTTP_ERRORS["invalid_api_key"].status_code,
            detail=HTTP_ERRORS["invalid_api_key"].detail,
        )
