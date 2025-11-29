from fastapi import APIRouter, UploadFile, File, HTTPException
from app.api.v1.schemas import TranscriptionResponse
from app.services import audio_service, transcription_service
import uuid
import time

from app.stats import stats # , processing_times

router = APIRouter()

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(file: UploadFile = File(..., description="Видеофайл для транскрибации.")):
    """
    Принимает видеофайл, извлекает из него аудиодорожку, транскрибирует речь и возвращает результат в виде текста.

    - **file**: Видеофайл, который необходимо обработать.
    """

    start = time.time()
    stats["requests_total"] += 1

    # Простая проверка типа контента видео.
    if not file.content_type or not file.content_type.startswith("video/"):
        stats["invalid_type_total"] += 1
        stats["errors_total"] += 1
        raise HTTPException(
            status_code=400, 
            detail=f"Неверный тип файла: {file.content_type}. Пожалуйста, загрузите видео."
        )
    
    # Проверка на пустой файл.
    contents = await file.read()
    await file.seek(0)
    if not contents:
        stats["empty_files_total"] += 1
        stats["errors_total"] += 1
        raise HTTPException(status_code=400, detail="Загруженный файл пуст.")
    file_size = len(contents)

    try:
        # Извлекаем аудио из загруженного видеофайла.
        audio_path = await audio_service.extract_audio(file)

        # Транскрибируем извлеченное аудио.
        transcription_result = transcription_service.transcribe_audio(audio_path)

        # Генерируем уникальный ID для видео.
        video_id = str(uuid.uuid4())

        # Метрики успеха
        stats["success_total"] += 1

        # Время обработки
        duration = time.time() - start
        # processing_times.append(duration)
        stats["last_processing_time"] = duration
        stats["avg_processing_time"] = 0 #sum(processing_times) / len(processing_times)

        # Форматируем и возвращаем ответ.
        return TranscriptionResponse(
            video_id=video_id,
            language=transcription_result["language"],
            transcript=transcription_result["transcript"],

            # ✔ добавляем недостающие поля
            processing_time=duration,
            file_size=file_size,
            stats=stats,
        )
    except Exception as e:
        stats["errors_total"] += 1

        duration = time.time() - start
        # processing_times.append(duration)
        stats["last_processing_time"] = duration
        stats["avg_processing_time"] = 0 #sum(processing_times) / len(processing_times)

        # Общий обработчик ошибок для перехвата исключений из сервисов.
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")
