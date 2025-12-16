from __future__ import annotations

import asyncio
import os
import requests

from app.services.job_store import dequeue_job, update_job
from app.services.job_notifier import notify_orchestrator
from app.services.audio_service import extract_audio_from_path
from app.services.stt_factory import get_stt_provider


async def _post_callback(url: str, payload: dict, timeout: int = 10) -> None:
    def _do():
        try:
            requests.post(url, json=payload, timeout=timeout)
        except Exception:
            pass

    await asyncio.to_thread(_do)


async def process_job(job):
    # job has: job_id, file_path, callback_url, stt_provider, ...
    update_job(job.job_id, status="processing", step="extract_audio", progress=35)
    notify_orchestrator(job.job_id, "EXTRACT_AUDIO", "IN_PROGRESS")

    audio_path = None
    try:
        # 1) extract audio
        audio_path, duration, _ = await extract_audio_from_path(job.file_path, delete_original=False)

        update_job(job.job_id, status="processing", step="transcribe", progress=70)
        notify_orchestrator(job.job_id, "TRANSCRIBE", "IN_PROGRESS")

        # 2) transcribe
        provider = get_stt_provider(job.stt_provider)
        result = await provider.transcribe(audio_path)

        update_job(job.job_id, status="processing", step="finalize", progress=90)
        notify_orchestrator(job.job_id, "FINALIZE", "IN_PROGRESS")

        # 3) success
        job_result = {
            "transcript": result.transcript,
            "language": result.language,
            "duration_sec": duration,
            "provider": getattr(provider, "get_name", lambda: None)(),
            "model": getattr(provider, "get_model_name", lambda: None)(),
            "device": getattr(provider, "get_device", lambda: None)(),
        }

        update_job(job.job_id, status="done", step="done", progress=100, result=job_result, error=None)
        notify_orchestrator(job.job_id, "DONE", "DONE", data=job_result)

        # 4) callback (optional)
        if job.callback_url:
            await _post_callback(
                job.callback_url,
                {"job_id": job.job_id, "status": "done", "result": job_result},
                timeout=10
            )

    except Exception as e:
        err = str(e)
        update_job(job.job_id, status="error", step="error", progress=100, error=err)
        notify_orchestrator(job.job_id, "ERROR", "FAIL", error=err)

        if job.callback_url:
          await _post_callback(
              job.callback_url,
              {"job_id": job.job_id, "status": "error", "error": err},
              timeout=10
          )

    finally:
        # cleanup temp wav
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass


async def worker_loop():
    print("Worker loop started")
    while True:
        try:
            job = await asyncio.to_thread(dequeue_job, 5)
            if job:
                await process_job(job)
        except Exception as e:
            print(f"Worker loop error: {e}")
            await asyncio.sleep(2)
