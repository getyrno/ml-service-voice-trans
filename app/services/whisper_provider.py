import os
import asyncio
import concurrent.futures
from faster_whisper import WhisperModel

from app.core import config
from app.services.stt_provider import STTProvider, TranscriptionResult


class WhisperProvider(STTProvider):
    def __init__(self):
        self._model: WhisperModel | None = None
        self._model_name: str | None = None
        self._device: str = "cpu"
        self._compute_type: str = "int8"
    
    def _load_model(self) -> None:
        if self._model is None:
            import torch
            import ctranslate2

            self._model_name = config.WHISPER_MODEL

            cuda_version = torch.version.cuda or "unknown"
            ct2_version = getattr(ctranslate2, "__version__", "unknown")

            if torch.cuda.is_available():
                self._device = "cuda"
                self._compute_type = "float16"
            else:
                self._device = "cpu"
                self._compute_type = "int8"

            print(
                f"[WhisperProvider] Инициализация. "
                f"model={self._model_name}, device={self._device}, "
                f"compute_type={self._compute_type}, "
                f"torch.cuda={cuda_version}, ctranslate2={ct2_version}"
            )

            try:
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
            except Exception as e:
                msg = str(e)
                if "libcudnn_ops" in msg or "cudnnCreateTensorDescriptor" in msg:
                    # Красиво ловим типичный кейс с несовместимыми CUDA/cuDNN/ctranslate2
                    raise STTInitError(
                        "Не удалось инициализировать Whisper на GPU: "
                        "похоже, несовместимы версии CUDA/cuDNN и ctranslate2. "
                        "Сейчас сервис ожидает стек: "
                        "образ nvidia/cuda:12.3.2-cudnn9-devel-ubuntu22.04, "
                        "torch==2.5.1+cu124, ctranslate2>=4.5.0. "
                        "Проверь конфигурацию контейнера."
                    ) from e
                # всё остальное пробрасываем как есть
                raise

            print("[WhisperProvider] Модель успешно загружена.")

    def _blocking_transcribe(self, audio_path: str) -> dict:
        segments, info = self._model.transcribe(
            audio_path,
            language="ru",
            task="transcribe",
            # vad_filter=True,
            # vad_parameters=dict(
            #     min_silence_duration_ms=400,
            # ),
        )

        # segments - это генератор, собираем текст
        text_parts = []
        for seg in segments:
            text_parts.append(seg.text)

        full_text = "".join(text_parts)

        return {
            "language": info.language or "ru",
            "transcript": full_text,
        }
    
    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
       
        Args:
            audio_path: Путь к аудиофайлу (WAV, 16kHz mono)
            
        Returns:
            TranscriptionResult с результатом распознавания
        """
        self._load_model()
        
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            try:
                result = await loop.run_in_executor(
                    pool, 
                    self._blocking_transcribe, 
                    audio_path
                )
            finally:
                # Удаляем временный файл после обработки
                if os.path.exists(audio_path):
                    os.remove(audio_path)
        
        return TranscriptionResult(
            language=result["language"],
            transcript=result["transcript"],
            provider=self.get_name()
        )
    
    def get_name(self) -> str:
        """Возвращает имя провайдера."""
        return "whisper"
    
    def get_device(self) -> str:
        """Возвращает устройство (cuda или cpu)."""
        return self._device
    
    def get_model_name(self) -> str:
        """Возвращает название модели Whisper."""
        return self._model_name or config.WHISPER_MODEL
    
    def is_loaded(self) -> bool:
        """Проверяет, загружена ли модель."""
        return self._model is not None


# Глобальный экземпляр для переиспользования (singleton)
_whisper_provider: WhisperProvider | None = None


def get_whisper_provider() -> WhisperProvider:
    """
    Возвращает глобальный экземпляр WhisperProvider.
    
    Использует паттерн singleton для переиспользования загруженной модели.
    """
    global _whisper_provider
    if _whisper_provider is None:
        _whisper_provider = WhisperProvider()
    return _whisper_provider


class STTInitError(RuntimeError):
    """Ошибка инициализации STT-модели (CUDA/cuDNN/ctranslate2 и т.п.)."""
    pass
