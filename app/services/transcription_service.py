import os
import whisper
import asyncio
import concurrent.futures

from app.core import config

model = None
_model_name: str | None = None

# ссылка на текущую задачу whisper
current_task: asyncio.Future | None = None


def load_model():
    """Ленивая загрузка Whisper."""
    global model, _model_name
    if model is None:
        _model_name = config.WHISPER_MODEL
        print(f"Загрузка модели Whisper ({_model_name})...")
        model = whisper.load_model(_model_name)
        print("Whisper загружен.")


def get_model_name() -> str:
    global _model_name
    return _model_name or config.WHISPER_MODEL


def get_model_device() -> str:
    global model
    if model is None:
        return "unknown"
    try:
        if hasattr(model, "device"):
            return str(model.device)
        import torch
        return str(next(model.parameters()).device)
    except Exception:
        return "unknown"


def _blocking_transcribe(audio_path: str) -> dict:
    """
    Синхронный вызов Whisper — выполняется в executor.
    """
    result = model.transcribe(audio_path, fp16=False)
    return {
        "language": result["language"],
        "transcript": result["text"],
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
