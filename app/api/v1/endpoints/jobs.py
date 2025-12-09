import os
import shutil
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.schemas.jobs import JobResponse, JobStatusResponse, JobStatus
from app.services.job_store import enqueue_job, get_job, Job
from app.services.job_notifier import notify_orchestrator
from app.core.config import UPLOAD_DIR

router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    file: UploadFile = File(...),
    callback_url: str | None = Form(None),
    stt_provider: str = Form("whisper"),
):
    """
    Создает новую джобу: сохраняет файл локально, кладет задачу в Redis.
    Возвращает ID джобы мгновенно.
    """
    job_id = str(uuid4())
    filename = file.filename or "video.mp4"
    # Безопасное имя файла
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-").strip()
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{safe_filename}")
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    job = Job(
        job_id=job_id,
        file_path=file_path,
        callback_url=callback_url,
        stt_provider=stt_provider
    )
    enqueue_job(job)
    notify_orchestrator(job_id, "QUEUED", "STARTED")
    
    return JobResponse(
        job_id=UUID(job_id),
        status=JobStatus.QUEUED,
        created_at=datetime.utcnow()
    )

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID):
    """
    Возвращает текущий статус джобы из Redis.
    (Для поллинга, если нет callback)
    """
    str_id = str(job_id)
    job = get_job(str_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    # Преобразуем строковый статус в Enum
    try:
        status_enum = JobStatus(job.status)
    except ValueError:
        status_enum = JobStatus.ERROR
        
    return JobStatusResponse(
        job_id=job_id,
        status=status_enum,
        result=job.result,
        error=job.error
    )
