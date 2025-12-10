# app/services/trigger_benchmark.py
from __future__ import annotations

import asyncio
import datetime as dt
import os
from pathlib import Path
from typing import Any, Dict

import requests

from app.core.config import settings
from benchmark.run_benchmark import run_benchmark_core


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


async def run_benchmark_and_push() -> Dict[str, Any]:
    """
    Запускает бенчмарк и отправляет сырые результаты в оркестратор.

    Оркестратор по URL settings.orchestrator_model_stat_url
    уже дальше сам формирует красивые графики/сообщения в Telegram.
    """

    # где лежат тестовые сэмплы и куда класть результаты
    samples_dir = Path(os.getenv("BENCHMARK_SAMPLES_DIR", "benchmark/test_samples"))
    output_dir = Path(os.getenv("BENCHMARK_OUTPUT_DIR", "benchmark/results"))

    # 1) Гоняем бенчмарк
    benchmark_data = await run_benchmark_core(
        samples_dir=samples_dir,
        output_dir=output_dir,
        whisper_only=False,
        gigaam_only=False,
    )

    # 2) Готовим payload для оркестратора
    payload: Dict[str, Any] = {
        "event_type": "model_stat",
        "env": settings.env_name,
        "timestamp": now_iso(),
        # можно добавить любую доп. инфу: имя сервиса, ветку, модель и т.п.
        "service": "ml-service-voice-trans",
        "data": benchmark_data,
    }

    url = getattr(
        settings,
        "orchestrator_model_stat_url",
        "http://147.45.235.55:9100/trigger/model_stat",
    )

    # 3) Отправляем запрос в оркестратор (через to_thread, чтобы не блокировать event loop)
    def _post() -> Dict[str, Any]:
        try:
            resp = requests.post(url, json=payload, timeout=30)
            return {
                "ok": resp.ok,
                "status_code": resp.status_code,
                "text": resp.text[:500],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    send_result = await asyncio.to_thread(_post)

    return {
        "benchmark": benchmark_data,
        "send_result": send_result,
    }
