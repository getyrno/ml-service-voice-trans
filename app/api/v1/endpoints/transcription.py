import asyncio
from fastapi import Request, APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from app.api.v1.schemas import TranscriptionResponse
from app.services import audio_service
from app.services.stt_factory import get_stt_provider, get_stt_provider_ab
from app.services.telemetry import send_transcribe_event
import uuid
import time
import os

router = APIRouter()

MAX_FILE_SIZE_BYTES = 1000 * 1024 * 1024  # 1000 MB


async def ensure_connected(request: Request):
    """
    Проверяем, не оборвал ли клиент соединение.
    Если да — убиваем FFmpeg и Whisper.
    """
    if await request.is_disconnected():

        # === FFmpeg: внешний процесс ===
        if getattr(audio_service, "current_proc", None):
            proc = audio_service.current_proc
            try:
                proc.kill()
            except Exception:
                pass

        raise HTTPException(499, "Клиент отключился")


def get_client_ip(request: Request) -> str:
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip

    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2...
        ip = x_forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    return request.client.host if request.client else "unknown"


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Видеофайл для транскрибации."),
    channel: str = Form("api"),
    user_id: str | None = Form(None),
    stt_provider: str | None = Form(None, description="STT провайдер: 'whisper', 'gigaam' или None (авто)"),
):
    start = time.time()

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"Неверный тип файла: {file.content_type}. Загрузите видео."
        )

    # Размер файла
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size == 0:
        raise HTTPException(400, "Файл пуст.")

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(400, "Максимальный размер файла — 1000 МБ.")

    video_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    client_ip = get_client_ip(request)
    
    if user_id is None:
        user_id = client_ip      # фоллбек: если не пришёл, берём IP
    try:
        # ---------- CLIENT CHECK ----------
        await ensure_connected(request)

        # ---------- 1) Extract audio ----------
        audio_path, duration_sec, ffmpeg_ms = await audio_service.extract_audio(file)

        await ensure_connected(request)

        # ---------- 2) STT (Whisper или GigaAM) ----------
        t_transcribe_start = time.time()
        
        # Если провайдер указан в запросе - используем его, иначе A/B режим
        if stt_provider:
            provider = get_stt_provider(stt_provider)
        else:
            provider = get_stt_provider_ab()
        
        transcription_result = await provider.transcribe(audio_path)
        transcribe_ms = int((time.time() - t_transcribe_start) * 1000)

        await ensure_connected(request)

        # ---------- Telemetry ----------
        total_ms = int((time.time() - start) * 1000)

        telemetry_payload = {
            "request_id": request_id,
            "video_id": video_id,
            "filename": file.filename,
            "filesize_bytes": file_size,
            "duration_sec": duration_sec,
            "content_type": file.content_type,
            "model_name": provider.get_model_name(),
            "model_device": provider.get_device(),
            "stt_provider": provider.get_name(),
            "language_detected": transcription_result.language,
            "latency_ms": total_ms,
            "transcribe_ms": transcribe_ms,
            "ffmpeg_ms": ffmpeg_ms,
            "success": True,
            "error_code": None,
            "error_message": None,
            "client_ip": client_ip,
            "channel": channel,
            "user_id": user_id
        }

        background_tasks.add_task(send_transcribe_event, telemetry_payload)

        # ---------- Response ----------
        return TranscriptionResponse(
            video_id=video_id,
            language=transcription_result.language,
            transcript=transcription_result.transcript,
            processing_time=time.time() - start,
            file_size=file_size,
            duration_sec=duration_sec,
        )

    except HTTPException:
        raise

    except asyncio.CancelledError:
        raise HTTPException(499, "Транскрибация отменена (клиент отключился).")

    except Exception as e:
        total_ms = int((time.time() - start) * 1000)

        error_payload = {
            "request_id": request_id,
            "video_id": video_id,
            "filename": getattr(file, "filename", None),
            "filesize_bytes": file_size,
            "duration_sec": None,
            "content_type": getattr(file, "content_type", None),
            "model_name": provider.get_model_name() if 'provider' in locals() else "unknown",
            "model_device": provider.get_device() if 'provider' in locals() else "unknown",
            "stt_provider": provider.get_name() if 'provider' in locals() else "unknown",
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
        raise HTTPException(500, f"Произошла ошибка: {str(e)}")
