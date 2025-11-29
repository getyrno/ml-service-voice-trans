from fastapi import Request, APIRouter, UploadFile, File, HTTPException
from app.api.v1.schemas import TranscriptionResponse
from app.services import audio_service, transcription_service
import uuid
import time

# from app.stats import stats # , processing_times

router = APIRouter()

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(
    request: Request,
    file: UploadFile = File(..., description="Видеофайл для транскрибации.")
):
    """
    Принимает видеофайл, извлекает аудиодорожку, транскрибирует речь
    и возвращает результат в виде текста.
    """

    start = time.time()

    # 1. Проверка типа контента
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"Неверный тип файла: {file.content_type}. Пожалуйста, загрузите видео."
        )

    # 2. Размер файла, не читая его содержимое
    file.file.seek(0, 2)          # в конец
    file_size = file.file.tell()  # размер в байтах
    file.file.seek(0)             # обратно в начало

    if file_size == 0:
        raise HTTPException(400, "Загруженный файл пуст.")

    try:
        # 3. Извлекаем аудио
        audio_path = await audio_service.extract_audio(file)

        # 4. Транскрибируем
        transcription_result = transcription_service.transcribe_audio(audio_path)

        video_id = str(uuid.uuid4())
        duration = time.time() - start

        return TranscriptionResponse(
            video_id=video_id,
            language=transcription_result["language"],
            transcript=transcription_result["transcript"],
            processing_time=duration,
            file_size=file_size,
        )
    except Exception as e:
        duration = time.time() - start
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")
