# app/services/telemetry.py
from __future__ import annotations

import os
from typing import Dict, Any

import requests

# URL для отправки телеметрии (если не задан - телеметрия отключена)
ORCH_URL = os.getenv("ORCHESTRATOR_URL", "")
ENV_NAME = os.getenv("ENV_NAME", "gpu-prod")
CLIENT_NAME = os.getenv("CLIENT_NAME", "home-pc")


def send_transcribe_event(payload: Dict[str, Any]) -> None:
    """
    Отправляет событие транскрибации в оркестратор.
    Любые ошибки игнорируем, чтобы не ломать основной API.
    """
    if not ORCH_URL:
        return

    enriched = {
        "env": ENV_NAME,
        "client": CLIENT_NAME,
        **payload,
    }

    try:
        requests.post(ORCH_URL, json=enriched, timeout=1.5)
    except Exception:
        # можно логировать в stdout, если захочешь
        pass
