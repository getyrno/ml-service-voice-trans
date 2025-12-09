import random
from typing import Literal

from app.core import config
from app.services.stt_provider import STTProvider
from app.services.whisper_provider import get_whisper_provider
from app.services.gigaam_provider import get_gigaam_provider


ProviderName = Literal["whisper", "gigaam"]


def get_stt_provider(provider_name: str | None = None) -> STTProvider:
    """
    Возвращает STT провайдер по имени или из конфигурации. Args:
        provider_name: Имя провайдера ('whisper' или 'gigaam').
                       Если None, используется значение из config.STT_PROVIDER.
    
    Returns:
        Экземпляр STTProvider
        
    Raises:
        ValueError: Если указан неизвестный провайдер
    """
    if provider_name is None:
        provider_name = getattr(config, 'STT_PROVIDER', 'whisper')
    
    provider_name = provider_name.lower()
    
    if provider_name == "whisper":
        return get_whisper_provider()
    elif provider_name == "gigaam":
        return get_gigaam_provider()
    else:
        raise ValueError(f"Неизвестный STT провайдер: {provider_name}. "
                        f"Поддерживаются: 'whisper', 'gigaam'")


def get_stt_provider_ab() -> STTProvider:
    """
    эта часть для аб теста. Возвращает STT провайдер с учетом A/B тестирования.
    
    Процент запросов, направляемых на GigaAM, определяется
    переменной окружения STT_AB_GIGAAM_PERCENT (0-100).
    
    Если STT_AB_GIGAAM_PERCENT = 0: всегда Whisper
    Если STT_AB_GIGAAM_PERCENT = 100: всегда GigaAM
    Если STT_AB_GIGAAM_PERCENT = 50: 50% Whisper, 50% GigaAM
    
    Returns:
        Экземпляр STTProvider (Whisper или GigaAM)
    """
    gigaam_percent = getattr(config, 'STT_AB_GIGAAM_PERCENT', 0)
    
    # Если A/B не настроен (0%), используем основной провайдер
    if gigaam_percent <= 0:
        return get_stt_provider()
    
    # Если 100% на GigaAM
    if gigaam_percent >= 100:
        return get_gigaam_provider()
    
    # Случайный выбор с учетом процента
    if random.randint(1, 100) <= gigaam_percent:
        return get_gigaam_provider()
    else:
        return get_whisper_provider()


def preload_provider(provider_name: str | None = None) -> None:

    provider = get_stt_provider(provider_name)
    
    if hasattr(provider, '_load_model'):
        provider._load_model()
