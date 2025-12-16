import os
import shutil
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.schemas.jobs import JobResponse, JobStatusResponse, JobStatus, JobsListResponse, JobSummary
from app.services.job_store import enqueue_job, get_job, update_job, append_event, Job, list_jobs
from app.services.job_notifier import notify_orchestrator
from app.core.config import UPLOAD_DIR

router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    file: UploadFile = File(...),
    callback_url: str | None = Form(None),
    stt_provider: str = Form("whisper"),
    channel: str = Form("api"),
    user_id: str | None = Form(None),
):
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
        progress=1,
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        result=None,
        error=None,
        events=[],
    )
    enqueue_job(job)

    append_event(job_id, "queued", "START", message=f"channel={channel}, user_id={user_id or 'unknown'}")
    notify_orchestrator(job_id, "QUEUED", "STARTED")

    return JobResponse(
        job_id=UUID(job_id),
        status=JobStatus.QUEUED,
        created_at=utc_now_iso()
    )

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID):
    j = get_job(str(job_id))
    if not j:
        raise HTTPException(404, "Job not found")

    try:
        status_enum = JobStatus(j.status)
    except ValueError:
        status_enum = JobStatus.ERROR

    return JobStatusResponse(
        job_id=job_id,
        status=status_enum,
        step=j.step,
        progress=j.progress,
        created_at=j.created_at,
        updated_at=j.updated_at,
        result=j.result,
        error=j.error,
        events=j.events or [],
    )

@router.get("/jobs", response_model=JobsListResponse)
async def list_recent_jobs(limit: int = 20):
    limit = max(1, min(100, int(limit)))
    jobs = list_jobs(limit=limit)
    items = [
        JobSummary(
            job_id=j.job_id,
            status=j.status,
            created_at=j.created_at,
            updated_at=j.updated_at
        )
        for j in jobs
    ]
    return JobsListResponse(items=items)
