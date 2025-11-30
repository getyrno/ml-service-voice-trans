# app/api/v1/endpoints/transcription.py
from fastapi import Request, APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.api.v1.schemas import TranscriptionResponse
from app.services import audio_service, transcription_service
from app.services.telemetry import send_transcribe_event
import uuid
import time

router = APIRouter()

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 МБ

def get_client_ip(request: Request) -> str:
    """
    Возвращает IP клиента, учитывая возможный reverse proxy.
    Приоритет:
    1) X-Real-IP
    2) первый IP из X-Forwarded-For
    3) request.client.host
    """
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip

    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2...
        ip = x_forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    if request.client:
        return request.client.host

    return "unknown"

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Видеофайл для транскрибации.")
):
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

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Максимальный размер файла — 500 МБ."
        )

    video_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    client_ip = get_client_ip(request)

    try:
        # 1) ffmpeg: извлекаем аудио и получаем длительность
        audio_path, duration_sec, ffmpeg_ms = await audio_service.extract_audio(file)

        # 2) whisper
        t_transcribe_start = time.time()
        transcription_result = transcription_service.transcribe_audio(audio_path)
        transcribe_ms = int((time.time() - t_transcribe_start) * 1000)

        # 3) общая латентность
        total_ms = int((time.time() - start) * 1000)

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
            "client_ip": client_ip
        }

        background_tasks.add_task(send_transcribe_event, telemetry_payload)

        duration_processing = time.time() - start

        return TranscriptionResponse(
            video_id=video_id,
            language=transcription_result["language"],
            transcript=transcription_result["transcript"],
            processing_time=duration_processing,
            file_size=file_size,
            duration_sec=duration_sec,
        )
    except Exception as e:
        total_ms = int((time.time() - start) * 1000)

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
            "client_ip": client_ip
        }
        background_tasks.add_task(send_transcribe_event, error_payload)

        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")
