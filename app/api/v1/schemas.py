from pydantic import BaseModel, Field
from typing import Dict, Any

class TranscriptionResponse(BaseModel):
    video_id: str = Field(..., description="Уникальный идентификатор обработанного видео.")
    language: str = Field(..., description="Распознанный язык аудио.")
    transcript: str = Field(..., description="Полный текст расшифровки.")

    processing_time: float = Field(..., description="Время обработки запроса в секундах.")
    file_size: int = Field(..., description="Размер загруженного видеофайла в байтах.")
    duration_sec: float = Field(..., description="Длительность видео в секундах.")
