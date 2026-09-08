import asyncio
import time
from typing import Optional

from backend.models import AnalysisJob
from backend.database import async_session
from backend.schemas import JobStatusResponse
from backend.services.fabric_service import run_fabric
from backend.services.youtube_service import fetch_transcript
from backend.services.rumble_service import download_and_transcribe
from backend.services.file_service import transcribe_file
from backend.services.web_scraper import scrape_text
from backend.services.metadata_service import fetch_video_metadata
from backend.services.cost_service import estimate_cost

_jobs: dict[str, asyncio.Task] = {}


async def get_job(job_id: str) -> Optional[JobStatusResponse]:
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job is None:
            return None
        return JobStatusResponse(
            id=job.id,
            source=job.source,
            url=job.url,
            pattern=job.pattern,
            status=job.status,
            transcript=job.transcript,
            result=job.result,
            error=job.error,
            metadata_json=job.metadata_json,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


async def list_jobs(source: Optional[str] = None, pattern: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[JobStatusResponse]:
    async with async_session() as session:
        from sqlalchemy import select, desc
        stmt = select(AnalysisJob)
        if source:
            stmt = stmt.where(AnalysisJob.source == source)
        if pattern:
            stmt = stmt.where(AnalysisJob.pattern == pattern)
        stmt = stmt.order_by(desc(AnalysisJob.created_at)).offset(offset).limit(limit)
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        return [
            JobStatusResponse(
                id=j.id,
                source=j.source,
                url=j.url,
                pattern=j.pattern,
                status=j.status,
                transcript=j.transcript,
                result=j.result,
                error=j.error,
                metadata_json=j.metadata_json,
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in jobs
        ]


async def start_analysis(source: str, url: str | None, pattern: str, file_path: str | None = None) -> str:
    async with async_session() as session:
        job = AnalysisJob(
            source=source,
            url=url,
            file_path=file_path,
            pattern=pattern,
            status="pending",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    task = asyncio.create_task(_run_analysis(job_id, source, url, pattern, file_path))
    _jobs[job_id] = task
    return job_id


async def _run_analysis(job_id: str, source: str, url: str | None, pattern: str, file_path: str | None):
    t0 = time.time()
    meta = {}

    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        job.status = "running"
        await session.commit()

    try:
        if source in ("youtube", "rumble") and url:
            try:
                meta = await asyncio.wait_for(fetch_video_metadata(url), timeout=10)
            except (asyncio.TimeoutError, Exception):
                meta = {}

        if source in ("youtube", "rumble") and url:
            transcript = await _find_existing_transcript(source, url)
        else:
            transcript = None

        if transcript is None:
            if source == "youtube":
                transcript = await fetch_transcript(url)
            elif source == "rumble":
                transcript = await download_and_transcribe(url)
            elif source == "file":
                transcript = await transcribe_file(file_path)
            elif source == "web":
                transcript = await scrape_text(url)
            else:
                raise ValueError(f"Unknown source: {source}")
        else:
            meta["transcript_source"] = "cache (from history)"

        result = await run_fabric(pattern, transcript)

        processing_time = round(time.time() - t0, 1)
        meta.update({
            "fabric_pattern": pattern,
            "processing_time_seconds": processing_time,
        })

        async with async_session() as session:
            job = await session.get(AnalysisJob, job_id)
            job.transcript = transcript
            job.result = result
            job.metadata_json = meta
            job.status = "completed"
            await session.commit()

        asyncio.create_task(_enrich_metadata(job_id, transcript, result, pattern))

    except Exception as e:
        processing_time = round(time.time() - t0, 1)
        meta.update({"fabric_pattern": pattern, "processing_time_seconds": processing_time})
        async with async_session() as session:
            job = await session.get(AnalysisJob, job_id)
            job.status = "failed"
            job.error = str(e)
            job.metadata_json = meta
            await session.commit()
    finally:
        _jobs.pop(job_id, None)


async def _find_existing_transcript(source: str, url: str) -> str | None:
    if not url:
        return None
    from sqlalchemy import select
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.url == url)
            .where(AnalysisJob.transcript.isnot(None))
            .where(AnalysisJob.status.in_(["completed"]))
            .order_by(AnalysisJob.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing and existing.transcript:
            return existing.transcript
    return None


async def _enrich_metadata(job_id: str, transcript: str, result: str, pattern: str):
    try:
        cost_info = await estimate_cost(transcript, result)
        async with async_session() as session:
            job = await session.get(AnalysisJob, job_id)
            if job and job.metadata_json:
                job.metadata_json.update(cost_info)
                await session.commit()
    except Exception:
        pass