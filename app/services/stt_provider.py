from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptionResult:
    """
    Результат транскрибации аудио.
    
    Attributes:
        language: Определенный язык аудио (например, 'ru', 'en')
        transcript: Распознанный текст
        provider: Имя провайдера, выполнившего транскрибацию
    """
    language: str
    transcript: str
    provider: str


class STTProvider(ABC):
    """
    Абстрактный базовый класс для STT провайдеров.
    
    Все провайдеры распознавания речи должны наследовать этот класс
    и реализовать его абстрактные методы.
    """
    
    @abstractmethod
    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
        Распознает речь из аудиофайла.
        
        Args:
            audio_path: Путь к аудиофайлу (WAV, 16kHz mono)
            
        Returns:
            TranscriptionResult с языком и распознанным текстом
            
        Raises:
            RuntimeError: При ошибке распознавания
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Возвращает имя провайдера для телеметрии и логирования.
        
        Returns:
            Имя провайдера (например, 'whisper', 'gigaam')
        """
        pass
    
    @abstractmethod
    def get_device(self) -> str:
        """
        Возвращает устройство, на котором работает модель.
        
        Returns:
            Имя устройства (например, 'cuda', 'cpu')
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Возвращает название/версию загруженной модели.
        
        Returns:
            Название модели (например, 'small', 'e2e_rnnt')
        """
        pass
    
    def is_loaded(self) -> bool:
        """
        Проверяет, загружена ли модель.
        
        Returns:
            True если модель загружена и готова к работе
        """
        return False
