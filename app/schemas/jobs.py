from __future__ import annotations

from dataclasses import Field
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

class JobEvent(BaseModel):
    step: str
    status: str
    ts_utc: str
    message: str | None = None

class JobResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: str

class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    step: str | None = None
    progress: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    events: list[JobEvent] = Field(default_factory=list)

class JobSummary(BaseModel):
    job_id: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None

class JobsListResponse(BaseModel):
    items: list[JobSummary]

class CallbackPayload(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
