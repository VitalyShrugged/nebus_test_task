import contextlib
import logging
import typing
from typing import Sequence, Type, TypeVar

from sqlalchemy import Result, RowMapping, text
from sqlalchemy.exc import ResourceClosedError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class PostgresGateway:
    """
    Обёртка над асинхронным движком SQLAlchemy: пул соединений, сессии, транзакции
    и хелперы для выполнения raw SQL с маппингом результата в pydantic-модели.

    Новую сессию нужно открывать на каждый запрос/юнит работы, через async_session()
    или get_dbsession_depends() (для FastAPI-зависимостей).
    """

    def __init__(
            self,
            username: str,
            password: str,
            host: str,
            database: str,
            port: int = 5432,
            application_name: str = "Python Local",
            pg_query_timeout: int = 15,  # максимальное время выполнения запроса / простоя в транзакции, минут
            create_connection_timeout: int = 60,
            pool_size: int = 5,
            pool_recycle: int = 1000,
            pool_timeout: int = 10,
            max_overflow: int = 2,
    ) -> None:
        self._autocommit = True

        self._username = username
        self._password = password
        self._host = host
        self._database = database
        self._port = port

        self._pool_size = pool_size
        self._pool_recycle = pool_recycle
        self._pool_timeout = pool_timeout
        self._max_overflow = max_overflow

        self._application_name = application_name
        self._create_connection_timeout = create_connection_timeout
        self._pg_query_timeout = pg_query_timeout

        self._build_engine()

    def _build_engine(self) -> None:
        dsn = f"postgresql+asyncpg://{self._username}:{self._password}@{self._host}:{self._port}/{self._database}"
        timeout_ms = str(self._pg_query_timeout * 60 * 1000)

        self._engine = create_async_engine(
            dsn,
            pool_size=self._pool_size,
            pool_recycle=self._pool_recycle,
            pool_timeout=self._pool_timeout,
            max_overflow=self._max_overflow,
            pool_pre_ping=True,
            connect_args={
                "timeout": self._create_connection_timeout,
                "statement_cache_size": 0,  # для совместимости с внешними пулерами вроде pgbouncer
                "server_settings": {
                    "application_name": self._application_name,
                    "statement_timeout": timeout_ms,
                    "idle_in_transaction_session_timeout": timeout_ms,
                },
            },
        )
        self._session_maker = async_sessionmaker(self._engine, expire_on_commit=False)

    @contextlib.asynccontextmanager
    async def async_session(self) -> typing.AsyncGenerator[AsyncSession, None]:
        """
        Открывает новую сессию БД.
        """
        async with self._session_maker() as session:
            yield session

    async def get_dbsession_depends(self) -> typing.AsyncGenerator[AsyncSession, None]:
        """
        Открывает сессию БД на время запроса. Использовать как FastAPI-зависимость,
        напрямую не вызывать.
        """
        async with self.async_session() as dbsession:
            yield dbsession

    @contextlib.asynccontextmanager
    async def transaction_context(self, db_session: AsyncSession) -> typing.AsyncGenerator[None, None]:
        try:
            self._autocommit = False
            yield
        except Exception as e:
            await db_session.rollback()
            raise e
        else:
            await db_session.commit()
        finally:
            self._autocommit = True

    async def execute(
            self,
            sql_query: str,
            db_session: AsyncSession | None = None,
            params: dict | None = None,
    ) -> Result:
        """
        Выполняет SQL-запрос. Если сессия не передана — открывает свою и коммитит сразу.
        """
        if db_session is not None:
            result = await db_session.execute(text(sql_query), params)
            if self._autocommit:
                await db_session.commit()
            return result

        async with self._session_maker() as session:
            result = await session.execute(text(sql_query), params)
            await session.commit()
            return result

    async def fetch_all(
            self,
            sql_query: str,
            db_session: AsyncSession | None = None,
            params: dict | None = None,
    ) -> Sequence[RowMapping]:
        """
        Выполняет SELECT и возвращает строки как последовательность dict-подобных объектов.
        """
        result = await self.execute(sql_query=sql_query, db_session=db_session, params=params)
        try:
            return result.mappings().all()
        except ResourceClosedError:
            return []

    async def fetch_one_as(
            self,
            model: Type[T],
            sql_query: str,
            db_session: AsyncSession | None = None,
            params: dict | None = None,
    ) -> T | None:
        """
        Выполняет SELECT и мапит первую строку результата в переданную pydantic-модель.
        """
        rows = await self.fetch_all(sql_query=sql_query, db_session=db_session, params=params)
        if not rows:
            return None
        try:
            return model(**dict(rows[0]))
        except Exception as e:
            logging.exception(f"Failed to build {model} from row: {e}")
            return None

    async def fetch_many_as(
            self,
            model: Type[T],
            sql_query: str,
            db_session: AsyncSession | None = None,
            params: dict | None = None,
    ) -> list[T]:
        """
        Выполняет SELECT и мапит каждую строку результата в переданную pydantic-модель.
        """
        rows = await self.fetch_all(sql_query=sql_query, db_session=db_session, params=params)
        objects: list[T] = []
        for row in rows:
            try:
                objects.append(model(**dict(row)))
            except ValidationError as e:
                logging.exception(f"Failed to build {model} from row: {e}")
        return objects
