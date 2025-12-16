import asyncio
import os
import requests

from app.services.job_store import dequeue_job, update_job, append_event
from app.services.job_notifier import notify_orchestrator
from app.services.audio_service import extract_audio_from_path
from app.services.stt_factory import get_stt_provider

async def process_job(job):
    update_job(job.job_id, status="processing", step="queued", progress=25)
    append_event(job.job_id, "job", "PROCESSING")
    notify_orchestrator(job.job_id, "PROCESSING", "IN_PROGRESS")

    audio_path = None
    try:
        # 1) Extract audio
        update_job(job.job_id, step="extract_audio", progress=35)
        append_event(job.job_id, "extract_audio", "START")
        audio_path, duration, _ = await extract_audio_from_path(job.file_path, delete_original=False)
        append_event(job.job_id, "extract_audio", "DONE")

        # 2) Transcribe
        update_job(job.job_id, step="transcribe", progress=70)
        append_event(job.job_id, "transcribe", "START")
        provider = get_stt_provider(job.stt_provider)
        result = await provider.transcribe(audio_path)
        append_event(job.job_id, "transcribe", "DONE")

        # 3) Finalize
        update_job(job.job_id, step="finalize", progress=90)
        append_event(job.job_id, "finalize", "START")

        job_result = {
            "transcript": result.transcript,
            "language": result.language,
            "duration_sec": duration
        }

        update_job(job.job_id, status="done", step="done", progress=100, result=job_result)
        append_event(job.job_id, "finalize", "DONE")
        append_event(job.job_id, "job", "DONE")
        notify_orchestrator(job.job_id, "DONE", "DONE", data=job_result)

        if job.callback_url:
            try:
                requests.post(job.callback_url, json={
                    "job_id": job.job_id,
                    "status": "done",
                    "result": job_result
                }, timeout=10)
            except Exception:
                pass

    except Exception as e:
        update_job(job.job_id, status="error", step="error", progress=100, error=str(e))
        append_event(job.job_id, "job", "ERROR", message=str(e))
        notify_orchestrator(job.job_id, "ERROR", "FAIL", error=str(e))

        if job.callback_url:
            try:
                requests.post(job.callback_url, json={
                    "job_id": job.job_id,
                    "status": "error",
                    "error": str(e)
                }, timeout=10)
            except Exception:
                pass

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
