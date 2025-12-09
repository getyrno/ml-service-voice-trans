from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class JobResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime

class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    progress: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

class CallbackPayload(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
