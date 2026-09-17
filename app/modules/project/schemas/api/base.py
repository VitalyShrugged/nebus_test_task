import json
from datetime import datetime

from pydantic import BaseModel
from app.modules.infra.logs.setting import logger


class CustomBaseModel(BaseModel):
    """
    Базовая модель с безопасным дампом.
    """

    def safe_dump(self) -> dict:
        """Возвращает дамп без несерилизуемых полей."""
        raw = super().model_dump()  # Тут вызывается super чтобы без рекурсий поднять model_dump из pydantic
        clean = dict()

        for key, value in raw.items():
            try:
                json.dumps(value)
                clean[key] = value
            except Exception:
                try:
                    if isinstance(value, datetime):
                        clean[key] = value
                    else:
                        logger.error(
                            f"Unserializable field skipped: key - {key} : value - {value} type - {type(value)}")
                except Exception:
                    logger.error(f"Unserializable field skipped: key - {key} : value - {value} type - {type(value)}")

        return clean

    def model_dump(self, *args, **kwargs) -> dict:
        """
        Переопределяем model_dump, чтобы при каждом вызове
        возвращался safe_dump.
        """
        return self.safe_dump()
