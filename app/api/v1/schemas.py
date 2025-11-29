from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    video_id: str = Field(..., description="Уникальный идентификатор обработанного видео.")
    language: str = Field(..., description="Распознанный язык аудио (например, \'ru\', \'en\').")
    transcript: str = Field(..., description="Полный текст расшифровки.")
