from fastapi import APIRouter, HTTPException

from backend.schemas import YouTubeRequest, JobStatusResponse
from backend.services.database_helpers import get_job, find_existing_result
from backend.services.youtube_orchestrator import run_youtube_analysis

router = APIRouter(prefix="/api/youtube")


@router.post("/analyze")
async def analyze_youtube(body: YouTubeRequest):
    job_id = await run_youtube_analysis(url=body.url, pattern=body.pattern, model=body.model)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_youtube_job(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_youtube_result(url: str, pattern: str, model: str | None = None):
    job = await find_existing_result("youtube", url, pattern, model)
    if job is None:
        return {"found": False}
    return {"found": True, "job": job}