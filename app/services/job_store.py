import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional

from app.services.redis_client import redis_client

QUEUE_KEY = "jobs:queue"
DATA_KEY = "jobs:data"
INDEX_KEY = "jobs:index"  # список последних job_id

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class Job:
    job_id: str
    file_path: str
    callback_url: Optional[str]
    stt_provider: str
    status: str = "queued"
    step: str = "queued"
    progress: int = 0
    created_at: str = ""
    updated_at: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    events: list[dict] = field(default_factory=list)

def enqueue_job(job: Job) -> None:
    now = utc_now_iso()
    job.created_at = now
    job.updated_at = now
    job.status = "queued"
    job.step = "queued"
    job.progress = 1
    job.events.append({"step": "job", "status": "CREATED", "ts_utc": now})

    redis_client.hset(DATA_KEY, job.job_id, json.dumps(asdict(job)))
    redis_client.lpush(QUEUE_KEY, job.job_id)

    # индекс последних jobs
    redis_client.lpush(INDEX_KEY, job.job_id)
    redis_client.ltrim(INDEX_KEY, 0, 99)  # храним последние 100

def dequeue_job(timeout: int = 5) -> Optional[Job]:
    result = redis_client.brpop(QUEUE_KEY, timeout=timeout)
    if not result:
        return None
    # result = (QUEUE_KEY, job_id)
    return get_job(result[1])

def get_job(job_id: str) -> Optional[Job]:
    data = redis_client.hget(DATA_KEY, job_id)
    return Job(**json.loads(data)) if data else None

def update_job(job_id: str, **updates) -> None:
    job = get_job(job_id)
    if not job:
        return

    for k, v in updates.items():
        setattr(job, k, v)
    job.updated_at = utc_now_iso()
    redis_client.hset(DATA_KEY, job_id, json.dumps(asdict(job)))

def append_event(job_id: str, step: str, status: str, message: str | None = None) -> None:
    job = get_job(job_id)
    if not job:
        return
    job.events.append({
        "step": step,
        "status": status,
        "ts_utc": utc_now_iso(),
        "message": message
    })
    job.updated_at = utc_now_iso()
    redis_client.hset(DATA_KEY, job_id, json.dumps(asdict(job)))

def list_jobs(limit: int = 20) -> list[Job]:
    ids = redis_client.lrange(INDEX_KEY, 0, max(0, limit - 1))
    jobs: list[Job] = []
    for jid in ids:
        j = get_job(jid)
        if j:
            jobs.append(j)
    return jobs
