from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.gemini_provider import GeminiProvider

def get_llm_provider(provider_type: str = None) -> BaseLLMProvider:
    provider = (provider_type or settings.LLM_PROVIDER).lower()
    if provider == "openai":
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    elif provider == "gemini":
        return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    elif provider == "mock":
        return MockLLMProvider()
    else:
        # Default fallback to mock for safety
        return MockLLMProvider()
