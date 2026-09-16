from fastapi import APIRouter

from backend.schemas import JobStatusResponse, PatternInfo
from backend.services.database_helpers import get_job, list_jobs, find_existing_result
from backend.services.fabric_service import list_patterns, list_models, DEFAULT_MODEL as FABRIC_DEFAULT_MODEL

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    from fastapi import HTTPException
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/history", response_model=list[JobStatusResponse])
async def get_history(source: str | None = None, pattern: str | None = None, limit: int = 50, offset: int = 0):
    return await list_jobs(source=source, pattern=pattern, limit=limit, offset=offset)


@router.get("/patterns", response_model=list[PatternInfo])
async def get_patterns():
    return await list_patterns()


@router.get("/models")
async def get_models():
    models = await list_models()
    return {"models": models, "default": FABRIC_DEFAULT_MODEL}