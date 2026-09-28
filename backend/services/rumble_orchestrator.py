import asyncio
import re
import time

from backend.services.database_helpers import (
    create_job, update_job_status, find_existing_job_id, find_existing_transcript,
)
from backend.services.rumble_service import download_and_transcribe
from backend.services.rumble_url import normalize
from backend.services.metadata_service import fetch_video_metadata
from backend.services.fabric_service import run_fabric
from backend.services.cost_service import estimate_cost

_jobs: dict[str, asyncio.Task] = {}


async def run_rumble_analysis(
    url: str, pattern: str, model: str | None = None, username: str | None = None
) -> str:
    # Store the canonical form so the caches key on the video, not on whatever
    # URL shape the browser happened to send.
    url = normalize(url) or url
    existing_id = await find_existing_job_id("rumble", url, pattern, model)
    if existing_id:
        return existing_id

    job_id = await create_job(source="rumble", url=url, pattern=pattern, username=username)
    task = asyncio.create_task(_pipeline(job_id, url, pattern, model))
    _jobs[job_id] = task
    return job_id


async def _pipeline(job_id: str, url: str, pattern: str, model: str | None):
    t0 = time.time()
    meta = {}
    transcript = None

    await update_job_status(job_id, "running")

    try:
        if not re.search(r'rumble\.com', url):
            raise ValueError(f"URL does not appear to be a Rumble URL: {url}")

        try:
            meta = await asyncio.wait_for(fetch_video_metadata(url), timeout=10)
        except (asyncio.TimeoutError, Exception):
            meta = {}

        transcript = await find_existing_transcript("rumble", url)

        if transcript is None:
            transcript, transcript_cost = await download_and_transcribe(url)
            meta["original_transcript_cost"] = round(transcript_cost, 6)

        result = await run_fabric(pattern, transcript, model=model)

        processing_time = round(time.time() - t0, 1)
        try:
            cost_info = await estimate_cost(transcript, result, model=model or None)
        except Exception:
            cost_info = {}
        meta.update({
            "fabric_pattern": pattern,
            "model": model,
            "processing_time_seconds": processing_time,
            **cost_info,
        })

        await update_job_status(job_id, "completed", transcript=transcript, result=result, metadata_json=meta)

    except Exception as e:
        processing_time = round(time.time() - t0, 1)
        meta.update({"fabric_pattern": pattern, "processing_time_seconds": processing_time})
        # Keep the transcript when we have one. Transcription is the paid step and
        # it already succeeded, so discarding it here would mean paying for the
        # same audio again on the next attempt.
        await update_job_status(
            job_id, "failed", error=str(e), transcript=transcript, metadata_json=meta
        )
    finally:
        _jobs.pop(job_id, None)