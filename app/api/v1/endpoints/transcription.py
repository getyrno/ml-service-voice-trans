# app/api/v1/endpoints/transcription.py
from fastapi import Request, APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.api.v1.schemas import TranscriptionResponse
from app.services import audio_service, transcription_service
from app.services.telemetry import send_transcribe_event
import uuid
import time

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Видеофайл для транскрибации.")
):
    """
    Принимает видеофайл, извлекает аудио, транскрибирует и:
      - возвращает результат клиенту,
      - отправляет событие в оркестратор.
    """
    start = time.time()

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"Неверный тип файла: {file.content_type}. Пожалуйста, загрузите видео.",
        )

    # размер файла
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size == 0:
        raise HTTPException(400, "Загруженный файл пуст.")

    video_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    try:
        # 1) ffmpeg
        audio_path, duration_sec, ffmpeg_ms = await audio_service.extract_audio(file)

        # 2) whisper
        t_transcribe_start = time.time()
        transcription_result = transcription_service.transcribe_audio(audio_path)
        transcribe_ms = int((time.time() - t_transcribe_start) * 1000)

        # 3) общая латентность
        total_ms = int((time.time() - start) * 1000)

        # 4) готовим payload для оркестратора
        telemetry_payload = {
            "request_id": request_id,
            "video_id": video_id,
            "filename": file.filename,
            "filesize_bytes": file_size,
            "duration_sec": duration_sec,
            "content_type": file.content_type,
            "model_name": transcription_service.get_model_name(),
            "model_device": transcription_service.get_model_device(),
            "language_detected": transcription_result["language"],
            "latency_ms": total_ms,
            "transcribe_ms": transcribe_ms,
            "ffmpeg_ms": ffmpeg_ms,
            "success": True,
            "error_code": None,
            "error_message": None,
        }

        # отправляем в фоне, чтобы не тормозить ответ
        background_tasks.add_task(send_transcribe_event, telemetry_payload)

        duration = time.time() - start

        return TranscriptionResponse(
            video_id=video_id,
            language=transcription_result["language"],
            transcript=transcription_result["transcript"],
            processing_time=duration,
            file_size=file_size,
        )
    except Exception as e:
        total_ms = int((time.time() - start) * 1000)

        # даже ошибки логируем в оркестратор
        error_payload = {
            "request_id": request_id,
            "video_id": video_id,
            "filename": getattr(file, "filename", None),
            "filesize_bytes": file_size,
            "duration_sec": None,
            "content_type": getattr(file, "content_type", None),
            "model_name": transcription_service.get_model_name(),
            "model_device": transcription_service.get_model_device(),
            "language_detected": None,
            "latency_ms": total_ms,
            "transcribe_ms": None,
            "ffmpeg_ms": None,
            "success": False,
            "error_code": "internal_error",
            "error_message": str(e),
        }
        background_tasks.add_task(send_transcribe_event, error_payload)

        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")
