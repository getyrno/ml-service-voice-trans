# app/services/audio_service.py
import ffmpeg
import tempfile
import os
import time
from typing import Tuple, Optional

from fastapi import UploadFile


async def extract_audio(video_file: UploadFile) -> tuple[str, Optional[float], int]:
    """
    Извлекает аудио из видеофайла и сохраняет его как временный WAV-файл (16kHz mono).

    Возвращает:
        audio_output_path: путь к временномy .wav
        duration_sec: длительность исходного видео (если удалось узнать), иначе None
        ffmpeg_ms: время работы ffmpeg в миллисекундах
    """
    # гарантируем начало
    await video_file.seek(0)

    suffix = os.path.splitext(video_file.filename or "")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_video_file:
        temp_video_path = temp_video_file.name
        chunk_size = 1024 * 1024  # 1MB

        while True:
            chunk = await video_file.read(chunk_size)
            if not chunk:
                break
            temp_video_file.write(chunk)

    video_size = os.path.getsize(temp_video_path)
    if video_size == 0:
        os.remove(temp_video_path)
        raise RuntimeError("Видео-файл пуст после копирования.")

    # пробуем узнать длительность видео
    duration_sec: Optional[float]
    try:
        probe = ffmpeg.probe(temp_video_path)
        duration_sec = float(probe["format"]["duration"])
    except Exception:
        duration_sec = None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file:
        audio_output_path = audio_file.name

    t0 = time.time()
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

        audio_size = os.path.getsize(audio_output_path)
        if audio_size == 0:
            raise RuntimeError("FFmpeg создал пустой WAV-файл.")
    except Exception:
        if os.path.exists(audio_output_path):
            os.remove(audio_output_path)
        raise
    finally:
        ffmpeg_ms = int((time.time() - t0) * 1000)
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

    return audio_output_path, duration_sec, ffmpeg_ms
