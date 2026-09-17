from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Базовый класс декларативных моделей SQLAlchemy 2.0.
    Используется только как источник схемы (metadata) для Alembic —
    сами запросы к БД в проекте идут через raw SQL (см. app/modules/db/postgres/functions).
    """
