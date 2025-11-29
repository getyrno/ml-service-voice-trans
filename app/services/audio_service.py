import ffmpeg
import tempfile
import os
from fastapi import UploadFile

async def extract_audio(video_file: UploadFile) -> str:
    """
    Извлекает аудио из видеофайла и сохраняет его как временный WAV-файл (16kHz mono).
    """

    # Гарантируем, что указатель в начале
    await video_file.seek(0)

    # Временный файл для видео
    suffix = os.path.splitext(video_file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_video_file:
        temp_video_path = temp_video_file.name
        chunk_size = 1024 * 1024  # 1MB

        while True:
            chunk = await video_file.read(chunk_size)
            if not chunk:
                break
            temp_video_file.write(chunk)

    # Проверим, что видео не пустое
    video_size = os.path.getsize(temp_video_path)
    if video_size == 0:
        os.remove(temp_video_path)
        raise RuntimeError("Видео-файл пуст после копирования.")

    # Временный файл для аудио
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file:
        audio_output_path = audio_file.name

    try:
        (
            ffmpeg
            .input(temp_video_path)
            .output(
                audio_output_path,
                format="wav",
                acodec="pcm_s16le",
                ac=1,
                ar=16000,
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        # Проверяем, что WAV реально получился
        audio_size = os.path.getsize(audio_output_path)
        if audio_size == 0:
            raise RuntimeError("FFmpeg создал пустой WAV-файл.")
    except Exception as e:
        if os.path.exists(audio_output_path):
            os.remove(audio_output_path)
        raise
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

    return audio_output_path
