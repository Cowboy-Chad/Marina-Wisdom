"""Canonical Rumble URLs, and the check that a video is on the permitted channel.

Both jobs here are about money.

1. **Normalisation.** The transcript cache is keyed on the URL string, and
   transcription is the expensive step. Rumble share links arrive with tracking
   parameters, trailing slashes, `www.`, and slug text that changes when a video
   is retitled. Without canonicalisation the same video is a different cache key
   each time and we pay to transcribe it again. The canonical form is the video
   id alone: https://rumble.com/v7f7p6q

2. **The channel check.** This app is only meant to analyse one channel, which
   caps the number of distinct transcriptions at roughly the size of that
   channel. A Rumble video URL contains no channel name, so membership is
   decided by reading the video's own page and looking for a link to the
   channel. That is deliberately not an allowlist scraped from the channel
   listing: ids vary in length, pagination drifts, and a scrape that comes back
   short would silently refuse legitimate videos. One page fetch per *new*
   video is cheaper and cannot go stale.
"""
import asyncio
import logging
import re
import time

logger = logging.getLogger(__name__)

CHANNEL_PATH = "/c/MarinaJacobi"

# Video ids are 'v' plus alphanumerics, and the length varies (vwgpdh, v7f7p6q),
# so do not pin it. The lookahead requires a delimiter or end so that a path like
# /videos?sort=views does not match as a video id.
_VIDEO_ID_RE = re.compile(
    r"rumble\.com/(?:embed/)?(v[a-z0-9]{4,12})(?=[-./]|$|[\"'?#])", re.IGNORECASE
)

# Path segments that look like a video id but are not.
_NOT_A_VIDEO = {"videos", "video", "view"}

# Videos confirmed to be on the channel, so a repeat submission within the TTL
# does not pay for another page fetch.
_verified: dict[str, float] = {}
_VERIFIED_TTL = 6 * 3600


def video_id(url: str | None) -> str | None:
    """Extract the Rumble video id, or None if this is not a Rumble video URL."""
    if not url:
        return None
    m = _VIDEO_ID_RE.search(url)
    if not m:
        return None
    vid = m.group(1).lower()
    return None if vid in _NOT_A_VIDEO else vid


def normalize(url: str | None) -> str | None:
    """Canonical form of a Rumble video URL: https://rumble.com/<video_id>.

    Returns None when the input is not a recognisable Rumble video URL, which
    callers should treat as a rejection rather than passing the raw string
    through, since a raw string would become a fresh cache key.

    Rumble redirects this slug-free form to the full title URL, so it stays
    usable as a link as well as a key.
    """
    vid = video_id(url)
    return f"https://rumble.com/{vid}" if vid else None


def _fetch_is_channel(webpage_url: str) -> bool:
    """Fetch a video page and report whether it belongs to the channel."""
    import cloudscraper

    scraper = cloudscraper.create_scraper()
    resp = scraper.get(webpage_url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"video page returned HTTP {resp.status_code}")
    return CHANNEL_PATH.lower() in resp.text.lower()


async def is_channel_video(url: str | None) -> tuple[bool, str]:
    """Decide whether a URL may be analysed.

    Returns (allowed, reason). Fails closed: a URL we cannot identify or cannot
    verify is refused, because every distinct video we accept is a transcription
    we pay for.
    """
    canonical = normalize(url)
    if canonical is None:
        return False, "That does not look like a Rumble video URL."

    vid = canonical.rsplit("/", 1)[-1]
    seen_at = _verified.get(vid)
    if seen_at and (time.time() - seen_at) < _VERIFIED_TTL:
        return True, ""

    try:
        on_channel = await asyncio.to_thread(_fetch_is_channel, canonical)
    except Exception as e:
        logger.warning("could not verify %s: %s", canonical, e)
        return False, (
            "Could not check that video against the channel just now, so it was "
            "refused. Please try again in a moment."
        )

    if not on_channel:
        return False, "This app only analyses videos from Marina Jacobi's official Rumble channel."

    _verified[vid] = time.time()
    return True, ""
