import os
import asyncio
import concurrent.futures
import torch

from app.core import config
from app.services.stt_provider import STTProvider, TranscriptionResult


class GigaAMProvider(STTProvider):
    """
    STT провайдер на базе GigaAM-v3 от Sber.варианты: e2e_rnnt, e2e_ctc, rnnt, ctc.
    """
    
    MODEL_ID = "ai-sage/GigaAM-v3"
    
    def __init__(self, model_variant: str | None = None):
        """Args:
            model_variant: Вариант модели (e2e_rnnt, e2e_ctc, rnnt, ctc).
                           По умолчанию берется из config.GIGAAM_MODEL_VARIANT.
        """
        self._model = None
        self._model_variant = model_variant or getattr(config, 'GIGAAM_MODEL_VARIANT', 'e2e_rnnt')
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def _load_model(self) -> None:
        """Ленивая :) загрузка модели GigaAM-v3."""
        if self._model is None:
            from transformers import AutoModel
            
            print(f"[GigaAMProvider] Загружаем GigaAM-v3 ({self._model_variant}) на {self._device}...")
            
            self._model = AutoModel.from_pretrained(
                self.MODEL_ID,
                revision=self._model_variant,
                trust_remote_code=True,
                torch_dtype=torch.float32,
            )
            
            self._model = self._model.float()
            
            if self._device == "cuda":
                self._model = self._model.cuda()
            
            print("[GigaAMProvider] Модель успешно загружена.")
    
    def _blocking_transcribe(self, audio_path: str) -> dict:
        transcription = self._model.transcribe_longform(audio_path)
        
        if isinstance(transcription, list):
            texts = []
            for seg in transcription:
                if isinstance(seg, dict) and 'transcription' in seg:
                    texts.append(seg['transcription'])
                elif isinstance(seg, str):
                    texts.append(seg)
            text = " ".join(texts)
        else:
            text = str(transcription) if transcription else ""
        
        # GigaAM-v3 обучен преимущественно на русском
        return {
            "language": "ru",
            "transcript": text,
        }
    
    async def transcribe(self, audio_path: str) -> TranscriptionResult:

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
        return "gigaam"
    
    def get_device(self) -> str:
        """Возвращает устройство (cuda или cpu)."""
        return self._device
    
    def get_model_name(self) -> str:
        """Возвращает название варианта модели."""
        return self._model_variant
    
    def is_loaded(self) -> bool:
        """Проверяет, загружена ли модель."""
        return self._model is not None


# Глобальный экземпляр для переиспользования (синглтон называтся)
_gigaam_provider: GigaAMProvider | None = None


def get_gigaam_provider() -> GigaAMProvider:
    """
    Возвращает глобальный экземпляр GigaAMProvider.
    
    """
    global _gigaam_provider
    if _gigaam_provider is None:
        _gigaam_provider = GigaAMProvider()
    return _gigaam_provider
