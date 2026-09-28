"""Honor-system registration and bearer-token sessions.

There are no passwords. Beta testers pick a username and give an email; the
username is the identity and the email is what proves it is the same person
coming back. That trade is deliberate — this gates a private community of
volunteers, and the expensive resource behind it (Marina's channel) is already
bounded and gated by its own allowlist, so a leaked account cannot run up a bill
the way an open transcription endpoint could.

The rate limit is therefore a runaway-loop guard rather than a security control.
"""
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.database import async_session
from backend.models import Session, User

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX_ANALYSES", "30"))
RATE_LIMIT_WINDOW = timedelta(seconds=int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "3600")))

# Tokens are stored hashed, so a database dump does not hand over live sessions.
# sha256 is right here (unlike for passwords): the input is 256 bits of entropy,
# so there is nothing to brute-force and no need for a slow KDF.


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for tz-aware columns.

    Comparing one against an aware `now` raises TypeError, so normalize on read.
    Postgres returns them aware already.
    """
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def clean_credentials(username: str, email: str) -> tuple[str, str]:
    """Validate and normalize, returning the trimmed values.

    Trimming happens before validation: a name pasted with surrounding
    whitespace is a normal thing for a person to do, and rejecting it reads as
    "your username is invalid" rather than "you have a trailing space".
    """
    username = (username or "").strip()
    email = (email or "").strip()

    if not USERNAME_RE.match(username):
        raise AuthError(
            400,
            "Username must be 3-32 characters, using letters, numbers, dots, dashes or underscores.",
        )
    if not EMAIL_RE.match(email):
        raise AuthError(400, "That does not look like an email address.")

    return username, email


async def register_or_login(username: str, email: str) -> tuple[User, str]:
    """Admit a returning tester, or create a new one. Returns (user, token).

    A username that already exists with the same email is the same person, so
    they are let back in — there is no password to forget. The same username
    with a *different* email is refused, so nobody can take over an identity
    they do not own. Usernames are matched case-insensitively.
    """
    username, email = clean_credentials(username, email)
    username_lower = username.lower()

    async with async_session() as db:
        result = await db.execute(select(User).where(User.username_lower == username_lower))
        user = result.scalar_one_or_none()

        if user is not None:
            if user.email.strip().lower() != email.lower():
                raise AuthError(
                    409,
                    "That username is already registered with a different email address.",
                )
        else:
            user = User(username=username, username_lower=username_lower, email=email)
            db.add(user)
            try:
                await db.flush()
            except IntegrityError:
                # Two first-time registrations of the same name raced. The other
                # one won; fall back to the returning-user path.
                await db.rollback()
                result = await db.execute(select(User).where(User.username_lower == username_lower))
                user = result.scalar_one_or_none()
                if user is None or user.email.strip().lower() != email.lower():
                    raise AuthError(409, "That username was just taken. Please pick another.")

        user.last_seen_at = datetime.now(timezone.utc)

        token = secrets.token_urlsafe(32)
        db.add(Session(token_hash=_hash_token(token), user_id=user.id))
        await db.commit()
        await db.refresh(user)

    return user, token


async def resolve_token(token: str | None) -> User | None:
    if not token:
        return None
    async with async_session() as db:
        result = await db.execute(
            select(User)
            .join(Session, Session.user_id == User.id)
            .where(Session.token_hash == _hash_token(token))
        )
        return result.scalar_one_or_none()


async def revoke_token(token: str) -> None:
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.token_hash == _hash_token(token)))
        session = result.scalar_one_or_none()
        if session is not None:
            await db.delete(session)
            await db.commit()


async def consume_quota(user: User) -> None:
    """Charge one unit against the user's fixed window, or raise 429."""
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user.id))
        fresh = result.scalar_one_or_none()
        if fresh is None:
            raise AuthError(401, "Your account no longer exists.")

        start = _as_aware(fresh.rate_window_start)
        if start is None or now - start >= RATE_LIMIT_WINDOW:
            fresh.rate_window_start = now
            fresh.rate_window_count = 1
        elif fresh.rate_window_count >= RATE_LIMIT_MAX:
            retry_in = int((start + RATE_LIMIT_WINDOW - now).total_seconds())
            raise AuthError(
                429,
                f"You have reached the limit of {RATE_LIMIT_MAX} analyses per "
                f"{int(RATE_LIMIT_WINDOW.total_seconds() // 60)} minutes. "
                f"Try again in about {max(retry_in // 60, 1)} minute(s).",
            )
        else:
            fresh.rate_window_count += 1

        await db.commit()
