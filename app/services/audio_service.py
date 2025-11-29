import ffmpeg
import tempfile
import os
from fastapi import UploadFile

async def extract_audio(video_file: UploadFile) -> str:
    """
    Извлекает аудио из видеофайла и сохраняет его как временный WAV-файл (16kHz mono).
    Безопасно для больших файлов.
    """

    # Читаем видео потоково (без загрузки всего файла в память)
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1]) as temp_video_file:
        chunk_size = 1024 * 1024  # 1MB
        while chunk := await video_file.read(chunk_size):
            temp_video_file.write(chunk)
        temp_video_path = temp_video_file.name

    # Создаем безопасный временный WAV-файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file:
        audio_output_path = audio_file.name

    try:
        # Используем ffmpeg для извлечения аудио, конвертируем в 16кГц моно WAV.
        ffmpeg.input(temp_video_path).output(
            audio_output_path, 
            format="wav",
            acodec='pcm_s16le', 
            ac=1, 
            ar='16000'
        ).run(capture_stdout=True, capture_stderr=True)
    except Exception as e:
        if os.path.exists(audio_output_path):
            os.remove(audio_output_path)
        raise e
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

    return audio_output_path
