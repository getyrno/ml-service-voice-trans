import os
from faster_whisper import WhisperModel

# Имя модели Whisper для использования в транскрипции.
# Варианты: "tiny", "base", "small", "medium", "large"
# Подробнее: https://github.com/openai/whisper
# WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
