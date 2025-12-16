from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from app.services.redis_client import redis_client

QUEUE_KEY = "jobs:queue"
DATA_KEY = "jobs:data"


@dataclass
class Job:
    job_id: str
    file_path: str
    callback_url: str | None
    stt_provider: str

    # for UI
    status: str = "queued"           # queued|processing|done|error
    step: str | None = None          # upload|queued|extract_audio|transcribe|finalize|done|error
    progress: int | None = None      # 0..100

    created_at: str = ""
    updated_at: str = ""

    result: dict | None = None
    error: str | None = None

    # optional metadata
    channel: str | None = None
    user_id: str | None = None


def enqueue_job(job: Job) -> None:
    now = datetime.utcnow().isoformat()
    job.created_at = now
    job.updated_at = now
    redis_client.hset(DATA_KEY, job.job_id, json.dumps(asdict(job), ensure_ascii=False))
    redis_client.lpush(QUEUE_KEY, job.job_id)


def dequeue_job(timeout: int = 5) -> Optional[Job]:
    # BRPOP returns (queue_key, value) or None
    res = redis_client.brpop(QUEUE_KEY, timeout=timeout)
    if not res:
        return None

    job_id = res[1]
    if isinstance(job_id, (bytes, bytearray)):
        job_id = job_id.decode("utf-8", errors="ignore")

    return get_job(str(job_id))


def get_job(job_id: str) -> Optional[Job]:
    data = redis_client.hget(DATA_KEY, job_id)
    if not data:
        return None

    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8", errors="ignore")

    payload = json.loads(data)
    return Job(**payload)


def update_job(job_id: str, **updates) -> None:
    job = get_job(job_id)
    if not job:
        return

    for k, v in updates.items():
        setattr(job, k, v)

    job.updated_at = datetime.utcnow().isoformat()
    redis_client.hset(DATA_KEY, job_id, json.dumps(asdict(job), ensure_ascii=False))
