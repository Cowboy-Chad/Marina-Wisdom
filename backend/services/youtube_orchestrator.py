import asyncio
import re
import time

from backend.services.database_helpers import (
    create_job, update_job_status, find_existing_job_id, find_existing_transcript,
)
from backend.services.youtube_service import fetch_transcript
from backend.services.metadata_service import fetch_video_metadata
from backend.services.fabric_service import run_fabric
from backend.services.cost_service import estimate_cost

_jobs: dict[str, asyncio.Task] = {}


async def run_youtube_analysis(url: str, pattern: str, model: str | None = None) -> str:
    existing_id = await find_existing_job_id("youtube", url, pattern, model)
    if existing_id:
        return existing_id

    job_id = await create_job(source="youtube", url=url, pattern=pattern)
    task = asyncio.create_task(_pipeline(job_id, url, pattern, model))
    _jobs[job_id] = task
    return job_id


async def _pipeline(job_id: str, url: str, pattern: str, model: str | None):
    t0 = time.time()
    meta = {}

    await update_job_status(job_id, "running")

    try:
        if not re.search(r'(youtube\.com|youtu\.be)', url):
            raise ValueError(f"URL does not appear to be a YouTube URL: {url}")

        try:
            meta = await asyncio.wait_for(fetch_video_metadata(url), timeout=10)
        except (asyncio.TimeoutError, Exception):
            meta = {}

        transcript = await find_existing_transcript("youtube", url)

        if transcript is None:
            transcript = await fetch_transcript(url)

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
        await update_job_status(job_id, "failed", error=str(e), metadata_json=meta)
    finally:
        _jobs.pop(job_id, None)