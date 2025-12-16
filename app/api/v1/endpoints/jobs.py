from __future__ import annotations

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

MAX_FILE_SIZE_BYTES = 1000 * 1024 * 1024  # 1000MB


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    file: UploadFile = File(...),
    callback_url: str | None = Form(None),
    stt_provider: str = Form("whisper"),

    # extra metadata (frontend sends it)
    channel: str | None = Form(None),
    user_id: str | None = Form(None),
):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(400, f"Неверный тип файла: {file.content_type}. Загрузите видео.")

    # size check (UploadFile has file-like)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size <= 0:
        raise HTTPException(400, "Файл пуст.")
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(400, "Максимальный размер файла — 1000 МБ.")

    job_id = str(uuid4())
    filename = file.filename or "video.mp4"
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-").strip()
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{safe_filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = Job(
        job_id=job_id,
        file_path=file_path,
        callback_url=callback_url,
        stt_provider=stt_provider,
        status="queued",
        step="queued",
        progress=20,          # upload finished on backend side
        channel=channel,
        user_id=user_id,
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
    job = get_job(str(job_id))
    if not job:
        raise HTTPException(404, "Job not found")
        
        
    # Преобразуем строковый статус в Enum

    # Преобразуем строковый статус в Enum
    try:
        status_enum = JobStatus(job.status)
    except ValueError:
        status_enum = JobStatus.ERROR

    created_at = None
    updated_at = None
    try:
        created_at = datetime.fromisoformat(job.created_at) if job.created_at else None
    except Exception:
        created_at = None
    try:
        updated_at = datetime.fromisoformat(job.updated_at) if job.updated_at else None
    except Exception:
        updated_at = None

    return JobStatusResponse(
        job_id=job_id,
        status=status_enum,
        step=job.step,
        progress=job.progress,
        result=job.result,
        error=job.error,
        created_at=created_at,
        updated_at=updated_at,
    )
