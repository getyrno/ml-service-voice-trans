import json
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, asdict
from app.services.redis_client import redis_client

QUEUE_KEY = "jobs:queue"
DATA_KEY = "jobs:data"

@dataclass
class Job:
    job_id: str
    file_path: str
    callback_url: str | None
    stt_provider: str
    status: str = "queued"
    created_at: str = ""
    result: dict | None = None
    error: str | None = None

def enqueue_job(job: Job) -> None:
    job.created_at = datetime.utcnow().isoformat()
    redis_client.hset(DATA_KEY, job.job_id, json.dumps(asdict(job)))
    redis_client.lpush(QUEUE_KEY, job.job_id)

def dequeue_job(timeout: int = 5) -> Job | None:
    result = redis_client.brpop(QUEUE_KEY, timeout=timeout)
    if not result:
        return None
    return get_job(result[1])

def get_job(job_id: str) -> Job | None:
    data = redis_client.hget(DATA_KEY, job_id)
    return Job(**json.loads(data)) if data else None

def update_job(job_id: str, **updates) -> None:
    if job := get_job(job_id):
        for k, v in updates.items():
            setattr(job, k, v)
        redis_client.hset(DATA_KEY, job_id, json.dumps(asdict(job)))
