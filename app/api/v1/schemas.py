from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    video_id: str = Field(..., description="Уникальный идентификатор обработанного видео.")
    language: str = Field(..., description="Распознанный язык аудио (например, \'ru\', \'en\').")
    transcript: str = Field(..., description="Полный текст расшифровки.")

    processing_time: float = Field(..., description="Время обработки запроса в секундах.")
    file_size: int = Field(..., description="Размер загруженного видеофайла в байтах.")
    stats: dict | None = Field(None, description="Глобальные метрики сервиса.")