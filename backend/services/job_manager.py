import asyncio
from typing import Optional

from backend.models import AnalysisJob
from backend.database import async_session
from backend.schemas import JobStatusResponse
from backend.services.fabric_service import run_fabric
from backend.services.youtube_service import fetch_transcript
from backend.services.rumble_service import download_and_transcribe
from backend.services.file_service import transcribe_file
from backend.services.web_scraper import scrape_text

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
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        job.status = "running"
        await session.commit()

    try:
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

        result = await run_fabric(pattern, transcript)

        async with async_session() as session:
            job = await session.get(AnalysisJob, job_id)
            job.transcript = transcript
            job.result = result
            job.status = "completed"
            await session.commit()
    except Exception as e:
        async with async_session() as session:
            job = await session.get(AnalysisJob, job_id)
            job.status = "failed"
            job.error = str(e)
            await session.commit()
    finally:
        _jobs.pop(job_id, None)