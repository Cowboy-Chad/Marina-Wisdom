import asyncio
import time

from backend.services.database_helpers import (
    create_job, update_job_status, find_existing_job_id,
)
from backend.services.web_scraper import scrape_text
from backend.services.fabric_service import run_fabric
from backend.services.cost_service import estimate_cost

_jobs: dict[str, asyncio.Task] = {}


async def run_web_analysis(url: str, pattern: str, model: str | None = None) -> str:
    existing_id = await find_existing_job_id("web", url, pattern, model)
    if existing_id:
        return existing_id

    job_id = await create_job(source="web", url=url, pattern=pattern)
    task = asyncio.create_task(_pipeline(job_id, url, pattern, model))
    _jobs[job_id] = task
    return job_id


async def _pipeline(job_id: str, url: str, pattern: str, model: str | None):
    t0 = time.time()
    meta = {}

    await update_job_status(job_id, "running")

    try:
        transcript = await scrape_text(url)

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