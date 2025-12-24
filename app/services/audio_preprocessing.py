"""
Модуль препроцессинга аудиосигнала.
Содержит функции для нормализации громкости аудио.
"""
import subprocess
import tempfile
import os
from typing import Optional


def normalize_audio_loudness(
    input_path: str,
    target_lufs: float = -16.0,
    output_path: Optional[str] = None
) -> str:
    """
    Нормализует громкость аудиофайла до заданного уровня LUFS.
    
    Использует ffmpeg с фильтром loudnorm для EBU R128 нормализации.
    
    Args:
        input_path: Путь к входному аудиофайлу
        target_lufs: Целевой уровень громкости в LUFS (по умолчанию -16.0)
        output_path: Путь для сохранения результата (если None - создается временный файл)
        
    Returns:
        Путь к нормализованному аудиофайлу
        
    Raises:
        RuntimeError: Если нормализация не удалась
    """
    if output_path is None:
        # Создаем временный файл с тем же расширением
        suffix = os.path.splitext(input_path)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            output_path = tmp.name
    
    # Построение команды ffmpeg с фильтром loudnorm
    # loudnorm - двухпроходный фильтр для точной нормализации по EBU R128
    cmd = [
        "ffmpeg",
        "-y",  # Перезаписывать выходной файл
        "-i", input_path,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        "-ar", "16000",  # Частота дискретизации 16kHz
        "-ac", "1",      # Моно
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка нормализации аудио: {e.stderr}")
    
    # Проверяем, что выходной файл создан и не пуст
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("FFmpeg не создал нормализованный файл или он пуст")
    
    return output_path


def get_audio_loudness(input_path: str) -> dict:
    """
    Измеряет текущий уровень громкости аудиофайла.
    
    Args:
        input_path: Путь к аудиофайлу
        
    Returns:
        Словарь с измерениями громкости (input_i, input_tp, input_lra, input_thresh)
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-af", "loudnorm=print_format=summary",
        "-f", "null",
        "-"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        # Парсим вывод для получения значений громкости
        stderr = result.stderr
        loudness_info = {}
        
        for line in stderr.split('\n'):
            if 'Input Integrated:' in line:
                loudness_info['input_i'] = line.split(':')[-1].strip().split()[0]
            elif 'Input True Peak:' in line:
                loudness_info['input_tp'] = line.split(':')[-1].strip().split()[0]
            elif 'Input LRA:' in line:
                loudness_info['input_lra'] = line.split(':')[-1].strip().split()[0]
        
        return loudness_info
    except Exception as e:
        return {"error": str(e)}
