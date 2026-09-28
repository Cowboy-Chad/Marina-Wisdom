import asyncio
import base64
import logging
import math
import os
import subprocess

import httpx

from backend.config import get_openrouter_api_key

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = get_openrouter_api_key()

OPENROUTER_BASE = os.environ.get("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1")

TRANSCRIPTION_MODEL = os.environ.get("TRANSCRIPTION_MODEL", "openai/gpt-audio-mini")

# Audio is sent base64-encoded inside a JSON body, which inflates it by ~33%, and
# OpenRouter rejects an oversized request with 413. The previous 600s chunks at
# 32kbps produced ~3.2MB bodies and 413'd on long Rumble videos. These defaults
# keep a clip near 900KB, and _transcribe_range splits further on demand so a
# clip can never be too large regardless of settings.
CHUNK_DURATION = int(os.environ.get("TRANSCRIPTION_CHUNK_SECONDS", "300"))  # 5 min
CHUNK_BITRATE = os.environ.get("TRANSCRIPTION_CHUNK_BITRATE", "24k")
MIN_CHUNK_SECONDS = int(os.environ.get("TRANSCRIPTION_MIN_CHUNK_SECONDS", "20"))
MAX_CONCURRENT_CHUNKS = int(os.environ.get("TRANSCRIPTION_CONCURRENCY", "4"))
MAX_RETRIES = int(os.environ.get("TRANSCRIPTION_MAX_RETRIES", "3"))

# Statuses worth retrying: rate limiting and transient upstream failures. A 413
# is handled by splitting instead, and other 4xx are permanent.
_RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504, 522, 524}


class _TooLarge(Exception):
    """The provider rejected the request as oversized."""


async def _get_audio_duration(path: str) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except ValueError:
        raise RuntimeError(f"could not read audio duration from {path}")


async def _extract_clip(src: str, start: float, duration: float, out_path: str) -> None:
    """Cut [start, start+duration) out of src as a small mono mp3."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", src,
        "-ac", "1",
        "-b:a", CHUNK_BITRATE,
        out_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    await proc.communicate()
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f"ffmpeg produced no audio for {start:.0f}s+{duration:.0f}s")


async def _transcribe_clip(audio_path: str) -> tuple[str, float]:
    """Send one clip to OpenRouter. Raises _TooLarge on 413."""
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": TRANSCRIPTION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe this audio verbatim. Return only the transcribed text.",
                    },
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "mp3"}},
                ],
            }
        ],
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{OPENROUTER_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as e:
            last_error = e
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"transcription request failed: {e}")
            await asyncio.sleep(2 ** attempt)
            continue

        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return text, data.get("usage", {}).get("cost", 0)

        if resp.status_code == 413:
            raise _TooLarge(resp.text[:200])

        if resp.status_code in _RETRY_STATUSES and attempt < MAX_RETRIES:
            last_error = f"HTTP {resp.status_code}"
            await asyncio.sleep(2 ** attempt)
            continue

        raise RuntimeError(
            f"OpenRouter transcription failed ({resp.status_code}): {resp.text[:500]}"
        )

    raise RuntimeError(f"transcription failed after {MAX_RETRIES} attempts: {last_error}")


async def _transcribe_range(
    src: str, start: float, duration: float, work_dir: str, depth: int = 0
) -> tuple[str, float]:
    """Transcribe a range, halving it if the provider says the clip is too large.

    Splitting recursively means an unexpectedly long or high-bitrate video
    degrades into more, smaller requests instead of failing outright.
    """
    clip_path = os.path.join(work_dir, f"clip_{int(start)}_{int(duration)}_{depth}.mp3")
    try:
        await _extract_clip(src, start, duration, clip_path)
        try:
            return await _transcribe_clip(clip_path)
        except _TooLarge:
            if duration <= MIN_CHUNK_SECONDS:
                raise RuntimeError(
                    f"audio at {start:.0f}s is still too large for the provider "
                    f"even at {duration:.0f}s"
                )
            half = duration / 2
            logger.info(
                "clip too large at %.0fs (%.0fs) — splitting in half", start, duration
            )
            first = await _transcribe_range(src, start, half, work_dir, depth + 1)
            second = await _transcribe_range(
                src, start + half, duration - half, work_dir, depth + 1
            )
            return (
                (first[0] + "\n\n" + second[0]).strip(),
                first[1] + second[1],
            )
    finally:
        if os.path.exists(clip_path):
            os.remove(clip_path)


async def transcribe_audio(audio_path: str) -> tuple[str, float]:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not found in fabric .env or environment")

    work_dir = os.path.join(os.path.dirname(audio_path), "chunks")
    os.makedirs(work_dir, exist_ok=True)

    duration = await _get_audio_duration(audio_path)
    count = max(1, math.ceil(duration / CHUNK_DURATION))
    ranges = [
        (i * CHUNK_DURATION, min(CHUNK_DURATION, duration - i * CHUNK_DURATION))
        for i in range(count)
    ]
    logger.info(
        "transcribing %.0fs as %s chunk(s) of up to %ss", duration, count, CHUNK_DURATION
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)

    async def _one(start: float, length: float) -> tuple[str, float]:
        async with semaphore:
            return await _transcribe_range(audio_path, start, length, work_dir)

    try:
        # Results come back in submission order, so the transcript stays in
        # sequence however the chunks interleave.
        results = await asyncio.gather(*(_one(s, d) for s, d in ranges))
        return "\n\n".join(t for t, _ in results), sum(c for _, c in results)
    finally:
        for name in os.listdir(work_dir):
            try:
                os.remove(os.path.join(work_dir, name))
            except OSError:
                pass
        try:
            os.rmdir(work_dir)
        except OSError:
            pass
