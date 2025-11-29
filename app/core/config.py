import os

# Имя модели Whisper для использования в транскрипции.
# Варианты: "tiny", "base", "small", "medium", "large"
# Подробнее: https://github.com/openai/whisper
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
