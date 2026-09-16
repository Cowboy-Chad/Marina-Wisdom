from fastapi import APIRouter, HTTPException

from backend.schemas import RumbleRequest, JobStatusResponse
from backend.services.database_helpers import get_job, find_existing_result
from backend.services.rumble_orchestrator import run_rumble_analysis

router = APIRouter(prefix="/api/rumble")


@router.post("/analyze")
async def analyze_rumble(body: RumbleRequest):
    job_id = await run_rumble_analysis(url=body.url, pattern=body.pattern, model=body.model)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_rumble_job(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_rumble_result(url: str, pattern: str, model: str | None = None):
    job = await find_existing_result("rumble", url, pattern, model)
    if job is None:
        return {"found": False}
    return {"found": True, "job": job}