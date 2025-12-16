import os
import asyncio
import concurrent.futures
from typing import Optional

from faster_whisper import WhisperModel

from app.core import config
from app.services.stt_provider import STTProvider, TranscriptionResult


class STTInitError(RuntimeError):
    """Ошибка инициализации STT-модели (CUDA/cuDNN/ctranslate2 и т.п.)."""
    pass


class WhisperProvider(STTProvider):
    """
    faster-whisper (CTranslate2) + Silero VAD (через onnxruntime CPU).

    Почему именно так:
    - VAD (vad_filter=True) режет тишину и сильно уменьшает "галлюцинации".
    - Чтобы не ловить GPU/CPU конфликт по onnxruntime — используем onnxruntime (CPU),
      и НЕ ставим onnxruntime-gpu. :contentReference[oaicite:3]{index=3}
    """

    def __init__(self):
        self._model: Optional[WhisperModel] = None
        self._model_name: Optional[str] = None
        self._device: str = "cpu"
        self._compute_type: str = "int8"

        # Один executor на провайдера (не создаём ThreadPoolExecutor на каждый запрос)
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        # Можно тюнить через env, но дефолты рабочие
        self._vad_enabled = os.getenv("WHISPER_VAD", "1") == "1"

        # VAD параметры (Silero). Можно смело тюнить под ваши ролики.
        # min_silence_duration_ms: чем меньше — тем агрессивнее вырезает паузы.
        # У faster-whisper дефолт довольно консервативный (режет длинную тишину), но
        # если у вас “молчит и болтает”, обычно помогает опустить до 400–800мс. :contentReference[oaicite:4]{index=4}
        self._vad_parameters = {
            "min_silence_duration_ms": int(os.getenv("WHISPER_VAD_MIN_SILENCE_MS", "600")),
            "speech_pad_ms": int(os.getenv("WHISPER_VAD_SPEECH_PAD_MS", "200")),
        }

        # “Антигаллюцинационные” пороги Whisper:
        # - no_speech_threshold: если вероятность <|nospeech|> высокая + низкая уверенность — считаем сегмент тишиной. :contentReference[oaicite:5]{index=5}
        # - log_prob_threshold / compression_ratio_threshold участвуют в логике "считаем декодинг проваленным" и триггерят ретраи/сбросы. :contentReference[oaicite:6]{index=6}
        self._no_speech_threshold = float(os.getenv("WHISPER_NO_SPEECH_THRESHOLD", "0.6"))
        self._log_prob_threshold = float(os.getenv("WHISPER_LOG_PROB_THRESHOLD", "-1.0"))
        self._compression_ratio_threshold = float(os.getenv("WHISPER_COMPRESSION_RATIO_THRESHOLD", "2.4"))

        # Очень полезно против “контекст потёк на паузах”
        # (часто рекомендуют отключать, если есть галлюцинации на разрывах). :contentReference[oaicite:7]{index=7}
        self._condition_on_previous_text = os.getenv("WHISPER_CONDITION_ON_PREV_TEXT", "0") == "1"

    def _load_model(self) -> None:
        if self._model is not None:
            return

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
            f"[WhisperProvider] Init. model={self._model_name}, device={self._device}, "
            f"compute_type={self._compute_type}, torch.cuda={cuda_version}, ctranslate2={ct2_version}"
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
                raise STTInitError(
                    "Не удалось инициализировать Whisper на GPU: вероятно, несовместимы CUDA/cuDNN и ctranslate2. "
                    "Ожидаем стек: nvidia/cuda:12.3.2-cudnn9-devel-ubuntu22.04 + ctranslate2>=4.5.0."
                ) from e
            raise

        print("[WhisperProvider] Model loaded OK.")

    def _blocking_transcribe(self, audio_path: str) -> dict:
        """
        ВАЖНО:
        - VAD (vad_filter=True) режет тишину до транскрибации.
        - no_speech_threshold / log_prob_threshold / compression_ratio_threshold помогают
          снижать мусор на "тишине". :contentReference[oaicite:8]{index=8}
        """
        if self._model is None:
            raise RuntimeError("Model not loaded")

        segments, info = self._model.transcribe(
            audio_path,
            language="ru",
            task="transcribe",

            # === КЛЮЧЕВОЕ: возвращаем VAD ===
            vad_filter=self._vad_enabled,
            vad_parameters=self._vad_parameters if self._vad_enabled else None,

            # === Антигаллюцинации/стабильность ===
            no_speech_threshold=self._no_speech_threshold,
            log_prob_threshold=self._log_prob_threshold,
            compression_ratio_threshold=self._compression_ratio_threshold,

            # часто помогает, чтобы “не продолжал мысль” после длинной паузы
            condition_on_previous_text=self._condition_on_previous_text,
        )

        text_parts = [seg.text for seg in segments]
        full_text = "".join(text_parts).strip()

        return {
            "language": (getattr(info, "language", None) or "ru"),
            "transcript": full_text,
        }

    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        self._load_model()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self._pool, self._blocking_transcribe, audio_path)

        # IMPORTANT:
        # Здесь файл НЕ удаляем, потому что в твоём job worker он удаляется в finally.
        # Если хочешь — можно вынести cleanup в одно место (worker / endpoint),
        # чтобы не было двойного удаления.
        return TranscriptionResult(
            language=result["language"],
            transcript=result["transcript"],
            provider=self.get_name()
        )

    def get_name(self) -> str:
        return "whisper"

    def get_device(self) -> str:
        return self._device

    def get_model_name(self) -> str:
        return self._model_name or config.WHISPER_MODEL

    def is_loaded(self) -> bool:
        return self._model is not None


# Singleton
_whisper_provider: Optional[WhisperProvider] = None


def get_whisper_provider() -> WhisperProvider:
    global _whisper_provider
    if _whisper_provider is None:
        _whisper_provider = WhisperProvider()
    return _whisper_provider
