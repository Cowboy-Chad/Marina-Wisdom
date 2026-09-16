import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from backend.schemas import JobStatusResponse
from backend.services.database_helpers import get_job
from backend.services.file_orchestrator import run_file_analysis

router = APIRouter(prefix="/api/file")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/analyze")
async def analyze_file(file: UploadFile = File(...), pattern: str = Form(...), model: str | None = Form(default=None)):
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    job_id = await run_file_analysis(file_path=file_path, pattern=pattern, model=model)
    return {"job_id": job_id, "status": "pending", "file_path": file_path}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_file_job(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job