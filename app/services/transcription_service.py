# app/services/transcription_service.py
import os
import whisper

from app.core import config

model = None
_model_name: str | None = None


def load_model():
    """Ленивая загрузка Whisper."""
    global model, _model_name
    if model is None:
        _model_name = config.WHISPER_MODEL
        print(f"Загрузка модели Whisper ({_model_name}) в первый раз...")
        model = whisper.load_model(_model_name)
        print("Модель Whisper успешно загружена.")


def get_model_name() -> str:
    global _model_name
    return _model_name or config.WHISPER_MODEL


def get_model_device() -> str:
    """Пробуем понять, на чём крутится модель (cpu / cuda:0 / unknown)."""
    global model
    if model is None:
        return "unknown"
    try:
        # новые версии whisper имеют атрибут device
        if hasattr(model, "device"):
            return str(model.device)
        # fallback через torch
        import torch  # noqa: F401
        return str(next(model.parameters()).device)
    except Exception:
        return "unknown"


def transcribe_audio(audio_path: str) -> dict:
    """
    Транскрибирует аудиофайл и удаляет его после использования.
    """
    global model
    load_model()

    try:
        result = model.transcribe(audio_path, fp16=False)
        return {
            "language": result["language"],
            "transcript": result["text"],
        }
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
