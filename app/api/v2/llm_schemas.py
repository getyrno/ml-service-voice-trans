from typing import Any, Dict, Optional
from pydantic import BaseModel

class LLMRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.1
    top_p: float = 0.9
    stop: Optional[list[str]] = None
    raw: bool = False  # если true — не пытаемся парсить JSON


class LLMResponse(BaseModel):
    text: str
    parsed: Optional[Dict[str, Any]] = None
