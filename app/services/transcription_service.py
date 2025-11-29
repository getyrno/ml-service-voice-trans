import whisper
import os

from app.core import config

# Модель загружается при первом запросе на транскрипцию,
# чтобы избежать проблем с потреблением памяти при запуске сервера.
model = None

def load_model():
    """Загружает модель Whisper, если она еще не была загружена."""
    global model
    if model is None:
        print(f"Загрузка модели Whisper ({config.WHISPER_MODEL}) в первый раз...")
        # Используется модель, указанная в конфигурации.
        model = whisper.load_model(config.WHISPER_MODEL)
        print("Модель Whisper успешно загружена.")

def transcribe_audio(audio_path: str) -> dict:
    """
    Убеждается, что модель загружена, транскрибирует аудиофайл, а затем удаляет файл.

    Args:
        audio_path: Путь к аудиофайлу.

    Returns:
        Словарь, содержащий детали транскрипции.
    """
    global model
    load_model()  # Загружаем модель, если она еще не в памяти.

    try:
        # Выполняем транскрипцию.
        result = model.transcribe(audio_path, fp16=False)
        
        return {
            "language": result["language"],
            "transcript": result["text"],
        }
    finally:
        # Убеждаемся, что временный аудиофайл всегда удаляется.
        if os.path.exists(audio_path):
            os.remove(audio_path)