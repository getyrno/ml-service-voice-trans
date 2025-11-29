import ffmpeg
import tempfile
import os
from fastapi import UploadFile

async def extract_audio(video_file: UploadFile) -> str:
    """
    Извлекает аудио из видеофайла и сохраняет его как временный WAV-файл.

    Args:
        video_file: Загруженный видеофайл.

    Returns:
        Путь к временному аудиофайлу.
    """
    # Создаем временный файл для хранения загруженного видео.
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1]) as temp_video_file:
        content = await video_file.read()
        temp_video_file.write(content)
        temp_video_path = temp_video_file.name

    # Создаем путь для вывода аудио.
    audio_output_path = tempfile.mktemp(suffix=".wav")

    try:
        # Используем ffmpeg для извлечения аудио, конвертируем в 16кГц моно WAV.
        ffmpeg.input(temp_video_path).output(
            audio_output_path, 
            acodec='pcm_s16le', 
            ac=1, 
            ar='16000'
        ).run(quiet=True, overwrite_output=True)
    except Exception as e:
        # Удаляем видеофайл в случае ошибки.
        os.remove(temp_video_path)
        raise e
    finally:
        # Всегда удаляем временный видеофайл.
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

    return audio_output_path
