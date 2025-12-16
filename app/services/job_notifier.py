from __future__ import annotations

import socket
import requests
from datetime import datetime

from app.core.config import ORCHESTRATOR_JOB_URL


def notify_orchestrator(job_id: str, step: str, status: str, error: str | None = None, data: dict | None = None):
    if not ORCHESTRATOR_JOB_URL:
        return

    payload = {
        "job_id": job_id,
        "step_code": step,
        "status": status,
        "origin": "gpu",
        "gpu_host": socket.gethostname(),
        "message": error,
        "data": data or {},
        "step_started_at_utc": datetime.utcnow().isoformat(),
    }

    try:
        requests.post(ORCHESTRATOR_JOB_URL, json=payload, timeout=2)
    except Exception:
        pass
