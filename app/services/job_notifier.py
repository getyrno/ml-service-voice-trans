import os
import socket
import requests
from datetime import datetime
from app.core.config import ORCHESTRATOR_JOB_URL

def notify_orchestrator(job_id: str, step: str, status: str, error: str = None, data: dict = None):
    if not ORCHESTRATOR_JOB_URL:
        return
    try:
        requests.post(ORCHESTRATOR_JOB_URL, json={
            "job_id": job_id,
            "step_code": step,
            "status": status,
            "origin": "gpu",
            "gpu_host": socket.gethostname(),
            "message": error,
            "data": data or {},
            "step_started_at_utc": datetime.utcnow().isoformat(),
        }, timeout=2)
    except Exception:
        pass
