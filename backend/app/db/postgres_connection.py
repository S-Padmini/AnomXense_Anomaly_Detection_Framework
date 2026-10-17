
import os
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from collections.abc import Iterator


# Load settings from backend/app/.env.
_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)
load_dotenv(_ENV_PATH, override=False)


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required PostgreSQL setting: {name}"
        )

    return value


@lru_cache(maxsize=1)
def get_postgres_engine() -> Engine:
    """Create a reusable engine for the external PostgreSQL database."""

    url = URL.create(
        drivername="postgresql+psycopg",
        username=_required_setting("POSTGRES_USER"),
        password=_required_setting("POSTGRES_PASSWORD"),
        host=_required_setting("POSTGRES_HOST"),
        port=int(_required_setting("POSTGRES_PORT")),
        database=_required_setting("POSTGRES_DB"),
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
        pool_recycle=1800,
        connect_args={"connect_timeout": 5},
    )


def get_postgres_schema() -> str:
    """Return the configured PostgreSQL schema."""

    return _required_setting("POSTGRES_SCHEMA")


def list_postgres_tables() -> list[str]:
    """List accessible ordinary tables in the configured schema."""

    engine = get_postgres_engine()
    schema = get_postgres_schema()

    try:
        with engine.connect() as connection:
            inspector = inspect(connection)

            return sorted(
                inspector.get_table_names(schema=schema)
            )

    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Unable to list PostgreSQL tables. Check database "
            "connectivity and schema permissions."
        ) from exc


def read_postgres_table(table_name: str) -> pd.DataFrame:
    """Read an approved table from the configured schema."""

    allowed_tables = list_postgres_tables()

    if table_name not in allowed_tables:
        raise ValueError(
            "The requested table is not available "
            "in the configured PostgreSQL schema."
        )

    engine = get_postgres_engine()
    schema = get_postgres_schema()

    try:
        return pd.read_sql_table(
            table_name=table_name,
            con=engine,
            schema=schema,
        )

    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"Unable to read PostgreSQL table '{table_name}'. "
            "Check table permissions and database connectivity."
        ) from exc


def iter_postgres_table_chunks(
    table_name: str, *, chunksize: int = 50_000, columns: list[str] | None = None
) -> Iterator[pd.DataFrame]:
    """Yield PostgreSQL rows in bounded DataFrame chunks.

    This helper is additive: the existing Phase 1 full-table loader remains
    unchanged for compatibility. Large-data workflows can migrate to this
    iterator incrementally after their consumers support chunk processing.
    """
    if not isinstance(chunksize, int) or chunksize < 1:
        raise ValueError("chunksize must be a positive integer.")

    allowed_tables = list_postgres_tables()
    if table_name not in allowed_tables:
        raise ValueError(
            "The requested table is not available in the configured PostgreSQL schema."
        )

    engine = get_postgres_engine()
    schema = get_postgres_schema()
    try:
        with engine.connect() as connection:
            # SQLAlchemy's table reflection safely quotes schema/table names.
            from sqlalchemy import MetaData, Table, select
            metadata = MetaData()
            table = Table(table_name, metadata, schema=schema, autoload_with=connection)
            selected = [table.c[name] for name in columns] if columns else list(table.c)
            statement = select(*selected).execution_options(stream_results=True)
            result = connection.execution_options(stream_results=True).execute(statement)
            names = list(result.keys())
            while True:
                rows = result.fetchmany(chunksize)
                if not rows:
                    break
                yield pd.DataFrame.from_records(rows, columns=names)
    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"Unable to stream PostgreSQL table '{table_name}'. Check table permissions and connectivity."
        ) from exc
