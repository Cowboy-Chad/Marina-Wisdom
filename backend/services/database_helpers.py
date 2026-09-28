from typing import Optional

from backend.models import AnalysisJob
from backend.database import async_session
from backend.schemas import JobStatusResponse
from backend.services.fabric_service import DEFAULT_MODEL


async def _job_to_response(job: AnalysisJob) -> JobStatusResponse:
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
        username=job.username,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def get_job(job_id: str) -> Optional[JobStatusResponse]:
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job is None:
            return None
        return await _job_to_response(job)


async def list_jobs(
    source: Optional[str] = None,
    pattern: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[JobStatusResponse]:
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
        return [await _job_to_response(j) for j in jobs]


async def find_existing_result(
    source: str, url: str | None, pattern: str, model: str | None
) -> JobStatusResponse | None:
    if not url:
        return None
    from sqlalchemy import select, desc
    requested = model or DEFAULT_MODEL
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.url == url)
            .where(AnalysisJob.pattern == pattern)
            .where(AnalysisJob.status == "completed")
            .where(AnalysisJob.result.isnot(None))
            .order_by(desc(AnalysisJob.created_at))
        )
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            stored = (job.metadata_json or {}).get("model")
            if stored == requested:
                return await _job_to_response(job)
            if stored is None and requested == DEFAULT_MODEL:
                return await _job_to_response(job)
    return None


async def find_existing_job_id(
    source: str, url: str | None, pattern: str, model: str | None
) -> str | None:
    if not url:
        return None
    from sqlalchemy import select, desc
    requested = model or DEFAULT_MODEL
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.url == url)
            .where(AnalysisJob.pattern == pattern)
            .where(AnalysisJob.status == "completed")
            .where(AnalysisJob.result.isnot(None))
            .order_by(desc(AnalysisJob.created_at))
        )
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            stored = (job.metadata_json or {}).get("model")
            if stored == requested:
                return job.id
            if stored is None and requested == DEFAULT_MODEL:
                return job.id
    return None


async def find_existing_transcript(source: str, url: str) -> str | None:
    if not url:
        return None
    from sqlalchemy import select
    async with async_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.source == source)
            .where(AnalysisJob.url == url)
            .where(AnalysisJob.transcript.isnot(None))
            # Deliberately not filtered on status. A transcript is saved as soon
            # as transcription succeeds, before the (cheap) fabric step runs, so
            # a row that later failed still holds a transcript we paid for.
            # Requiring "completed" here would discard it and pay again.
            .order_by(AnalysisJob.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing and existing.transcript:
            return existing.transcript
    return None


async def create_job(
    source: str,
    url: str | None,
    pattern: str,
    file_path: str | None = None,
    username: str | None = None,
) -> str:
    async with async_session() as session:
        job = AnalysisJob(
            source=source,
            url=url,
            file_path=file_path,
            pattern=pattern,
            status="pending",
            username=username,
        )
        session.add(job)
        await session.commit()
        return job.id


async def update_job_status(job_id: str, status: str, **extra_fields):
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job:
            job.status = status
            for k, v in extra_fields.items():
                setattr(job, k, v)
            await session.commit()