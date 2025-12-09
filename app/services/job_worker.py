import asyncio
import os
import requests
from app.services.job_store import dequeue_job, update_job, get_job
from app.services.job_notifier import notify_orchestrator
from app.services.audio_service import extract_audio_from_path
from app.services.stt_factory import get_stt_provider

async def process_job(job):
    update_job(job.job_id, status="processing")
    notify_orchestrator(job.job_id, "PROCESSING", "IN_PROGRESS")
    
    audio_path = None
    try:
        # 1. FFmpeg: извлекаем аудио, оригинал не удаляем (вдруг ретрай)
        audio_path, duration, _ = await extract_audio_from_path(job.file_path, delete_original=False)
        
        # 2. STT: транскрибируем
        provider = get_stt_provider(job.stt_provider)
        result = await provider.transcribe(audio_path)
        
        # 3. Успех
        job_result = {
            "transcript": result.transcript,
            "language": result.language,
            "duration_sec": duration
        }
        update_job(job.job_id, status="done", result=job_result)
        notify_orchestrator(job.job_id, "DONE", "DONE", data=job_result)
        
        # 4. Callback
        if job.callback_url:
            try:
                requests.post(
                    job.callback_url,
                    json={
                        "job_id": job.job_id,
                        "status": "done",
                        "result": job_result
                    },
                    timeout=10
                )
            except Exception:
                pass # Не смогли доставить callback, но работа сделана
            
    except Exception as e:
        # Ошибка
        update_job(job.job_id, status="error", error=str(e))
        notify_orchestrator(job.job_id, "ERROR", "FAIL", error=str(e))
        
        if job.callback_url:
            try:
                requests.post(
                    job.callback_url,
                    json={
                        "job_id": job.job_id,
                        "status": "error",
                        "error": str(e)
                    },
                    timeout=10
                )
            except Exception:
                pass
    finally:
        # Чистим временный wav файл
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass
        
        # Опционально: можно чистить исходный файл, если мы уверены что job завершен
        # Но для дебага пока оставим или будем чистить по cron'у
        # if os.path.exists(job.file_path):
        #    os.remove(job.file_path)


async def worker_loop():
    print("Worker loop started")
    while True:
        try:
            # используем asyncio.to_thread для блокирующего вызова dequeue_job
            job = await asyncio.to_thread(dequeue_job, 5)
            if job:
                await process_job(job)
        except Exception as e:
            print(f"Worker loop error: {e}")
            await asyncio.sleep(5)
