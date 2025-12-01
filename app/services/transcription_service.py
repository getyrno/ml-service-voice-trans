import os
# import whisper
import asyncio
import concurrent.futures
from faster_whisper import WhisperModel
from app.core import config

model = None
_model_name: str | None = None

# ссылка на текущую задачу whisper
current_task: asyncio.Future | None = None


def load_model():
    """Ленивая загрузка FasterWhisper."""
    global model, _model_name
    if model is None:
        _model_name = config.WHISPER_MODEL
        print(f"Загружаем FasterWhisper: {_model_name} (fp16, cuda)...")
        model = WhisperModel(_model_name, device="cuda", compute_type="float16")
        print("Модель успешно загружена.")


def get_model_name() -> str:
    global _model_name
    return _model_name or config.WHISPER_MODEL


def get_model_device() -> str:
    global model
    if model is None:
        return "unknown"
    try:
        # у WhisperModel нет .device как у torch.nn.Module, но на всякий случай:
        if hasattr(model, "device"):
            return str(model.device)
    except Exception:
        pass
    return "cuda"  # раз мы всегда создаём с device="cuda"


def _blocking_transcribe(audio_path: str) -> dict:
    """
    Синхронный вызов Whisper — выполняется в executor.
    """
    # faster-whisper возвращает (segments, info)
    segments, info = model.transcribe(
        audio_path,
        language="ru",
        task="transcribe",
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=400,
        ),
    )


    # segments — это генератор, собираем текст
    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)

    full_text = "".join(text_parts)

    return {
        "language": info.language or "ru",
        "transcript": full_text,
    }

async def transcribe_audio_async(audio_path: str) -> dict:
    """
    Асинхронная транскрибация Whisper.
    Позволяет отменять выполнение (interrupt).
    """
    global current_task, model

    load_model()

    loop = asyncio.get_event_loop()

    # запускаем транскрибацию в отдельном thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        current_task = loop.run_in_executor(pool, _blocking_transcribe, audio_path)

        try:
            result = await current_task
        except asyncio.CancelledError:
            # Whisper не даёт прямого API для прерывания
            # но thread будет убит при завершении pool context manager
            raise
        finally:
            current_task = None
            if os.path.exists(audio_path):
                os.remove(audio_path)

    return result