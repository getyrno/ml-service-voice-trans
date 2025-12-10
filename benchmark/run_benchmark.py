#!/usr/bin/env python3
"""
Бенчмарк для сравнения STT провайдеров.

Запуск:
    python benchmark/run_benchmark.py --samples benchmark/test_samples/ --output benchmark/results/

Требования:
    - Аудио/видео файлы в директории test_samples
    - Установленные зависимости (requirements.txt)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.stt_provider import TranscriptionResult
from app.services.whisper_provider import WhisperProvider
from app.services.gigaam_provider import GigaAMProvider
from app.services import audio_service


@dataclass
class BenchmarkResult:
    """Результат бенчмарка одного файла."""
    filename: str
    provider: str
    model_name: str
    device: str
    duration_sec: Optional[float]
    transcribe_time_sec: float
    transcript: str
    language: str
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Сводка по результатам бенчмарка."""
    total_files: int
    successful: int
    failed: int
    avg_time_sec: float
    total_duration_sec: float
    realtime_factor: float  # время обработки / длительность аудио


async def extract_audio_from_file(file_path: str) -> tuple[str, Optional[float]]:
    """
    Извлекает аудио из файла (видео или аудио).
    
    Returns:
        tuple: (путь к WAV, длительность в секундах)
    """
    import tempfile
    import shutil
    
    # Создаем временную копию файла
    suffix = Path(file_path).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copy(file_path, tmp.name)
        tmp_path = tmp.name
    
    try:
        import subprocess
        
        # Получаем длительность через ffprobe
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", tmp_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.stdout.strip() else None
        
        # Конвертируем в WAV 16kHz mono
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_tmp:
            wav_path = wav_tmp.name
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", tmp_path,
            "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
            wav_path
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
        
        return wav_path, duration
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def benchmark_provider(
    provider_class,
    audio_path: str,
    filename: str,
    duration_sec: Optional[float]
) -> BenchmarkResult:
    """
    Запускает бенчмарк для одного провайдера и файла.
    """
    provider = provider_class()
    
    try:
        # Копируем аудио файл, так как провайдер удаляет его после обработки
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            shutil.copy(audio_path, tmp.name)
            tmp_audio_path = tmp.name
        
        start = time.time()
        result = await provider.transcribe(tmp_audio_path)
        elapsed = time.time() - start
        
        return BenchmarkResult(
            filename=filename,
            provider=provider.get_name(),
            model_name=provider.get_model_name(),
            device=provider.get_device(),
            duration_sec=duration_sec,
            transcribe_time_sec=elapsed,
            transcript=result.transcript,
            language=result.language,
        )
    except Exception as e:
        return BenchmarkResult(
            filename=filename,
            provider=provider.get_name(),
            model_name=provider.get_model_name(),
            device=provider.get_device(),
            duration_sec=duration_sec,
            transcribe_time_sec=0,
            transcript="",
            language="",
            error=str(e),
        )


def calculate_summary(results: List[BenchmarkResult]) -> BenchmarkSummary:
    """Вычисляет сводную статистику."""
    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]
    
    total_time = sum(r.transcribe_time_sec for r in successful)
    total_duration = sum(r.duration_sec or 0 for r in successful)
    
    return BenchmarkSummary(
        total_files=len(results),
        successful=len(successful),
        failed=len(failed),
        avg_time_sec=total_time / len(successful) if successful else 0,
        total_duration_sec=total_duration,
        realtime_factor=total_time / total_duration if total_duration > 0 else 0,
    )


def generate_markdown_report(
    whisper_results: List[BenchmarkResult],
    gigaam_results: List[BenchmarkResult],
    output_path: str
) -> None:
    """Генерирует Markdown отчет со сравнением."""
    whisper_summary = calculate_summary(whisper_results)
    gigaam_summary = calculate_summary(gigaam_results)
    
    report = f"""# Сравнение STT провайдеров

**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Сводка

| Метрика | Whisper | GigaAM |
|---------|---------|--------|
| Файлов обработано | {whisper_summary.successful}/{whisper_summary.total_files} | {gigaam_summary.successful}/{gigaam_summary.total_files} |
| Среднее время (сек) | {whisper_summary.avg_time_sec:.2f} | {gigaam_summary.avg_time_sec:.2f} |
| Коэффициент реального времени | {whisper_summary.realtime_factor:.2f}x | {gigaam_summary.realtime_factor:.2f}x |

> Коэффициент реального времени < 1.0 означает, что обработка быстрее реального времени.

## Детальные результаты

### Whisper

| Файл | Время (сек) | Длительность | Язык |
|------|-------------|--------------|------|
"""
    
    for r in whisper_results:
        status = "❌" if r.error else "✅"
        report += f"| {status} {r.filename} | {r.transcribe_time_sec:.2f} | {r.duration_sec or 0:.1f}s | {r.language} |\n"
    
    report += """
### GigaAM

| Файл | Время (сек) | Длительность | Язык |
|------|-------------|--------------|------|
"""
    
    for r in gigaam_results:
        status = "❌" if r.error else "✅"
        report += f"| {status} {r.filename} | {r.transcribe_time_sec:.2f} | {r.duration_sec or 0:.1f}s | {r.language} |\n"
    
    report += """
## Примеры транскрипции

"""
    for w, g in zip(whisper_results, gigaam_results):
        if w.error or g.error:
            continue
        report += f"""### {w.filename}

**Whisper:**
> {w.transcript[:500]}{"..." if len(w.transcript) > 500 else ""}

**GigaAM:**
> {g.transcript[:500]}{"..." if len(g.transcript) > 500 else ""}

---

"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ Отчет сохранен: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Бенчмарк STT провайдеров")
    parser.add_argument("--samples", required=True, help="Директория с тестовыми файлами")
    parser.add_argument("--output", required=True, help="Директория для результатов")
    parser.add_argument("--whisper-only", action="store_true", help="Тестировать только Whisper")
    parser.add_argument("--gigaam-only", action="store_true", help="Тестировать только GigaAM")
    args = parser.parse_args()
    
    samples_dir = Path(args.samples)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Поиск аудио/видео файлов
    extensions = {".mp4", ".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac"}
    files = [f for f in samples_dir.iterdir() if f.suffix.lower() in extensions]
    
    if not files:
        print(f"❌ Не найдено аудио/видео файлов в {samples_dir}")
        print(f"   Поддерживаемые форматы: {', '.join(extensions)}")
        return
    
    print(f"📁 Найдено файлов: {len(files)}")
    
    whisper_results = []
    gigaam_results = []
    
    for file_path in files:
        print(f"\n🎬 Обработка: {file_path.name}")
        
        # Извлекаем аудио
        audio_path, duration = await extract_audio_from_file(str(file_path))
        print(f"   Длительность: {duration:.1f}s" if duration else "   Длительность: неизвестно")
        
        try:
            # Whisper
            if not args.gigaam_only:
                print("   🔊 Whisper...")
                result = await benchmark_provider(
                    WhisperProvider, audio_path, file_path.name, duration
                )
                whisper_results.append(result)
                if result.error:
                    print(f"   ❌ Ошибка: {result.error}")
                else:
                    print(f"   ✅ {result.transcribe_time_sec:.2f}s")
            
            # GigaAM
            if not args.whisper_only:
                print("   🔊 GigaAM...")
                result = await benchmark_provider(
                    GigaAMProvider, audio_path, file_path.name, duration
                )
                gigaam_results.append(result)
                if result.error:
                    print(f"   ❌ Ошибка: {result.error}")
                else:
                    print(f"   ✅ {result.transcribe_time_sec:.2f}s")
        finally:
            # Удаляем временный WAV
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    # Сохраняем результаты
    if whisper_results:
        with open(output_dir / "whisper_results.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in whisper_results], f, ensure_ascii=False, indent=2)
    
    if gigaam_results:
        with open(output_dir / "gigaam_results.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in gigaam_results], f, ensure_ascii=False, indent=2)
    
    # Генерируем отчет
    if whisper_results and gigaam_results:
        generate_markdown_report(
            whisper_results, 
            gigaam_results,
            str(output_dir / "comparison.md")
        )
    
    print("\n✅ Бенчмарк завершен!")


if __name__ == "__main__":
    asyncio.run(main())

async def run_benchmark_core(
    samples_dir: Path,
    output_dir: Path,
    whisper_only: bool = False,
    gigaam_only: bool = False,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Поиск аудио/видео файлов
    extensions = {".mp4", ".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac"}
    files = [f for f in samples_dir.iterdir() if f.suffix.lower() in extensions]

    if not files:
        raise RuntimeError(
            f"Не найдено аудио/видео файлов в {samples_dir}. "
            f"Поддерживаемые форматы: {', '.join(extensions)}"
        )

    print(f"📁 Найдено файлов: {len(files)}")

    whisper_results: List[BenchmarkResult] = []
    gigaam_results: List[BenchmarkResult] = []

    for file_path in files:
        print(f"\n🎬 Обработка: {file_path.name}")

        # Извлекаем аудио
        audio_path, duration = await extract_audio_from_file(str(file_path))
        print(f"   Длительность: {duration:.1f}s" if duration else "   Длительность: неизвестно")

        try:
            # Whisper
            if not gigaam_only:
                print("   🔊 Whisper...")
                result = await benchmark_provider(
                    WhisperProvider, audio_path, file_path.name, duration
                )
                whisper_results.append(result)
                if result.error:
                    print(f"   ❌ Ошибка: {result.error}")
                else:
                    print(f"   ✅ {result.transcribe_time_sec:.2f}s")

            # GigaAM
            if not whisper_only:
                print("   🔊 GigaAM...")
                result = await benchmark_provider(
                    GigaAMProvider, audio_path, file_path.name, duration
                )
                gigaam_results.append(result)
                if result.error:
                    print(f"   ❌ Ошибка: {result.error}")
                else:
                    print(f"   ✅ {result.transcribe_time_sec:.2f}s")
        finally:
            # Удаляем временный WAV
            if os.path.exists(audio_path):
                os.remove(audio_path)

    # Сохраняем результаты как раньше
    if whisper_results:
        with open(output_dir / "whisper_results.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in whisper_results], f, ensure_ascii=False, indent=2)

    if gigaam_results:
        with open(output_dir / "gigaam_results.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in gigaam_results], f, ensure_ascii=False, indent=2)

    if whisper_results and gigaam_results:
        generate_markdown_report(
            whisper_results,
            gigaam_results,
            str(output_dir / "comparison.md"),
        )

    # Сводки для оркестратора
    whisper_summary = calculate_summary(whisper_results) if whisper_results else None
    gigaam_summary = calculate_summary(gigaam_results) if gigaam_results else None

    print("\n✅ Бенчмарк завершен!")

    return {
        "whisper_results": [asdict(r) for r in whisper_results],
        "gigaam_results": [asdict(r) for r in gigaam_results],
        "whisper_summary": asdict(whisper_summary) if whisper_summary else None,
        "gigaam_summary": asdict(gigaam_summary) if gigaam_summary else None,
    }