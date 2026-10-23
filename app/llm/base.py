from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseLLMProvider(ABC):
    """Abstract interface for LLM adapters."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.0
    ) -> str:
        """Generates a text completion from the language model."""
        pass
