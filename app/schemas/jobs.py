from __future__ import annotations

from enum import Enum
from typing import Any, Optional
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
    step: Optional[str] = None
    progress: Optional[int] = None  # 0..100
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CallbackPayload(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
