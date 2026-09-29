import asyncio
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


def _database_url() -> tuple[str, dict]:
    """Resolve the database URL and any engine connect args.

    Deployed, `DATABASE_URL` is set — Render injects a Postgres URL from the
    database in render.yaml. Locally it is unset and the app falls back to a
    SQLite file in the repo root, so there is nothing to configure to run it.
    The same `create_all` builds either schema, which is what makes the two
    interchangeable rather than two code paths.

    The Postgres rewriting below exists because managed providers hand out
    `postgres://` URLs, sometimes carrying `?sslmode=require`. SQLAlchemy's
    async engine needs the `postgresql+asyncpg://` scheme, and asyncpg does not
    understand `sslmode` as a query parameter, so it is translated into an `ssl`
    connect arg instead. Getting that wrong is an opaque startup failure, hence
    the explicit translation.
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


if not is_postgres():
    # SQLite's defaults assume one process at a time: readers block writers, and
    # a writer that finds the database locked gives up immediately.
    #
    # This is hardening, not a fix for an observed failure. I could not make the
    # default configuration fail — 200 concurrent writes and a deliberately slow
    # write transaction overlapping six others all succeeded, because the writes
    # this app performs last microseconds. It is still worth setting: WAL lets
    # the read-heavy history queries run while a job is being written, and
    # busy_timeout turns a rare collision into a short wait instead of an error
    # the user would see as a failed analysis.
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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


_CONNECT_ATTEMPTS = 20
_CONNECT_DELAY = 3.0


async def init_db(attempts: int = _CONNECT_ATTEMPTS, delay: float = _CONNECT_DELAY) -> None:
    """Create any missing tables, waiting for the database to accept connections.

    Deployed, Render provisions the web service and the database at the same
    time, so this regularly runs before the database is listening. Without the
    retry the app exits during startup and Render marks the deploy failed — which
    is what happened on the first deploy, where the database came up seven
    seconds after the service asked for it.

    Retrying is safe because everything here is idempotent: create_all only
    creates missing tables, and _apply_added_columns skips columns that already
    exist. A failed attempt leaves nothing half-done that a later one would
    trip over. Only connection failures are retried — a genuine schema error
    still fails immediately rather than being buried under two minutes of
    sleeping.
    """
    from backend.models import Base
    from sqlalchemy.exc import OperationalError

    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await _apply_added_columns(conn)
            if attempt > 1:
                print(f"[db] connected on attempt {attempt}")
            return
        except (OperationalError, OSError) as exc:
            # OSError covers a refused connection or a DNS failure; OperationalError
            # is what SQLAlchemy wraps most other connection problems in.
            if attempt == attempts:
                print(f"[db] still unreachable after {attempts} attempts, giving up")
                raise
            print(f"[db] not accepting connections yet (attempt {attempt}/{attempts}): {exc}")
            await asyncio.sleep(delay)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
