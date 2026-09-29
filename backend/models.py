import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Every datetime column is declared timezone=True, which is not cosmetic.
# Without it the column is TIMESTAMP WITHOUT TIME ZONE and asyncpg refuses to
# store the aware datetimes this app produces: its encoder subtracts a naive
# epoch (`delta = obj - pg_epoch_datetime` in asyncpg's datetime.pyx) and raises
# "can't subtract offset-naive and offset-aware datetimes". That surfaced as a
# 500 on registration against Postgres while working fine on SQLite, which
# stores whatever it is handed. With timezone=True the column is TIMESTAMP WITH
# TIME ZONE and the aware epoch is subtracted instead, which accepts them.
#
# The migration in database.py converts the columns on an existing database —
# create_all will not alter a table that already exists.


class User(Base):
    """A beta tester admitted through the honor-system registration form.

    There are no passwords and no email verification: this gates a private
    community of volunteers, not the public internet. The username is the
    identity and the email is what proves it is the same person returning.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=False)
    # Uniqueness is enforced on the lowercased form so "Dana" and "dana" cannot
    # both exist. A unique constraint on a derived column works identically on
    # SQLite and Postgres, unlike a functional index.
    username_lower = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_seen_at = Column(DateTime(timezone=True), default=_utcnow)

    # Fixed-window rate limit, kept on the row so it survives restarts and needs
    # no extra infrastructure.
    rate_window_start = Column(DateTime(timezone=True), nullable=True)
    rate_window_count = Column(Integer, default=0, nullable=False)


class Session(Base):
    """A bearer token issued at registration. Only the hash is stored."""

    __tablename__ = "sessions"

    token_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)  # rumble
    url = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    pattern = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | running | completed | failed
    transcript = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    # Who asked for it. History stays shared/global; this is attribution only,
    # so a surprising bill can be traced back to a person.
    username = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
