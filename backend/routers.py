import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from backend.schemas import AnalysisRequest, JobStatusResponse, PatternInfo
from backend.services import job_manager
from backend.services.fabric_service import list_patterns, list_models, DEFAULT_MODEL as FABRIC_DEFAULT_MODEL

router = APIRouter(prefix="/api")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/analyze")
async def analyze(request: AnalysisRequest):
    job_id = await job_manager.start_analysis(
        source=request.source,
        url=request.url,
        pattern=request.pattern,
        model=request.model,
    )
    return {"job_id": job_id, "status": "pending"}


@router.post("/analyze/file")
async def analyze_file(file: UploadFile = File(...), pattern: str = Form(...), model: str | None = Form(default=None)):
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    job_id = await job_manager.start_analysis(
        source="file",
        url=None,
        pattern=pattern,
        file_path=file_path,
        model=model,
    )
    return {"job_id": job_id, "status": "pending", "file_path": file_path}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/history", response_model=list[JobStatusResponse])
async def get_history(source: str | None = None, pattern: str | None = None, limit: int = 50, offset: int = 0):
    return await job_manager.list_jobs(source=source, pattern=pattern, limit=limit, offset=offset)


@router.get("/patterns", response_model=list[PatternInfo])
async def get_patterns():
    return await list_patterns()


@router.get("/models")
async def get_models():
    models = await list_models()
    return {"models": models, "default": FABRIC_DEFAULT_MODEL}