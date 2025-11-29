from fastapi import APIRouter, UploadFile, File, HTTPException
from app.api.v1.schemas import TranscriptionResponse
from app.services import audio_service, transcription_service
import uuid

router = APIRouter()

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(file: UploadFile = File(..., description="Видеофайл для транскрибации.")):
    """
    Принимает видеофайл, извлекает из него аудиодорожку, транскрибирует речь и возвращает результат в виде текста.

    - **file**: Видеофайл, который необходимо обработать.
    """
    # Простая проверка типа контента видео.
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400, 
            detail=f"Неверный тип файла: {file.content_type}. Пожалуйста, загрузите видео."
        )
    
    # Проверка на пустой файл.
    contents = await file.read()
    await file.seek(0)
    if not contents:
        raise HTTPException(status_code=400, detail="Загруженный файл пуст.")

    try:
        # Извлекаем аудио из загруженного видеофайла.
        audio_path = await audio_service.extract_audio(file)

        # Транскрибируем извлеченное аудио.
        transcription_result = transcription_service.transcribe_audio(audio_path)

        # Генерируем уникальный ID для видео.
        video_id = str(uuid.uuid4())

        # Форматируем и возвращаем ответ.
        return TranscriptionResponse(
            video_id=video_id,
            language=transcription_result["language"],
            transcript=transcription_result["transcript"],
        )
    except Exception as e:
        # Общий обработчик ошибок для перехвата исключений из сервисов.
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")
