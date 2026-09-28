from fastapi import APIRouter, Depends, HTTPException

from backend.models import User
from backend.schemas import RumbleRequest, JobStatusResponse
from backend.services.auth_service import AuthError, consume_quota
from backend.services.database_helpers import (
    get_job, find_existing_result, find_existing_transcript,
)
from backend.services.dependencies import get_current_user
from backend.services.rumble_orchestrator import run_rumble_analysis
from backend.services.rumble_url import normalize, is_channel_video

router = APIRouter(prefix="/api/rumble")


@router.post("/analyze")
async def analyze_rumble(body: RumbleRequest, user: User = Depends(get_current_user)):
    canonical = normalize(body.url)
    if canonical is None:
        raise HTTPException(
            status_code=400, detail="That does not look like a Rumble video URL."
        )

    # A video we have already transcribed is let through without re-checking the
    # channel, so a scraper outage cannot lock the community out of videos it has
    # already used. Anything new has to be on the channel: each distinct video we
    # accept is a transcription we pay for.
    if not await find_existing_transcript("rumble", canonical):
        allowed, reason = await is_channel_video(canonical)
        if not allowed:
            raise HTTPException(status_code=400, detail=reason)

    # Charged only once the request is known to be valid, so a typo or a
    # rejected channel does not eat into someone's allowance.
    try:
        await consume_quota(user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    job_id = await run_rumble_analysis(
        url=canonical, pattern=body.pattern, model=body.model, username=user.username
    )
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_rumble_job(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/check-result")
async def check_rumble_result(url: str, pattern: str, model: str | None = None):
    job = await find_existing_result("rumble", normalize(url) or url, pattern, model)
    if job is None:
        return {"found": False}
    return {"found": True, "job": job}
