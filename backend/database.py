import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


def _database_url() -> tuple[str, dict]:
    """Resolve the database URL and any engine connect args.

    Deployment uses Postgres (Render injects DATABASE_URL); local development
    falls back to SQLite in the repo root, so nothing has to be set up to run it.

    Render hands out `postgres://` URLs carrying `?sslmode=require`. SQLAlchemy's
    async engine needs the `postgresql+asyncpg://` scheme, and asyncpg does not
    understand `sslmode` as a query parameter, so it is translated into an `ssl`
    connect arg instead. Getting this wrong is an opaque connection failure at
    startup, which is why it is done explicitly here.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        path = os.path.join(os.path.dirname(__file__), "..", "cve_osint.db")
        return f"sqlite+aiosqlite:///{path}", {}

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    connect_args: dict = {}
    if url.startswith("postgresql+asyncpg://"):
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query))
        sslmode = query.pop("sslmode", None)
        if sslmode and sslmode != "disable":
            connect_args["ssl"] = True
        url = urlunparse(parsed._replace(query=urlencode(query)))

    return url, connect_args


DATABASE_URL, _CONNECT_ARGS = _database_url()

_engine_kwargs = {"echo": False, "connect_args": _CONNECT_ARGS}
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    # Managed Postgres drops idle connections; check before handing one out.
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = 300

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def is_postgres() -> bool:
    return DATABASE_URL.startswith("postgresql+asyncpg://")


# Columns added to analysis_jobs after the table was first created. create_all()
# only ever creates missing tables — it will not alter an existing one — so these
# are applied by hand. Local SQLite holds transcripts that were paid for, which
# rules out dropping and recreating the table.
_ADDED_COLUMNS = [
    ("analysis_jobs", "username", "VARCHAR"),
]


async def _apply_added_columns(conn) -> None:
    from sqlalchemy import inspect

    def _sync(sync_conn) -> None:
        inspector = inspect(sync_conn)
        tables = set(inspector.get_table_names())
        for table, column, ddl in _ADDED_COLUMNS:
            if table not in tables:
                continue
            if column in {c["name"] for c in inspector.get_columns(table)}:
                continue
            sync_conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            print(f"[db] added column {table}.{column}")

    await conn.run_sync(_sync)


async def init_db():
    from backend.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_added_columns(conn)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
