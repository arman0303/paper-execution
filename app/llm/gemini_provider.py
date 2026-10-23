import os
import json
from typing import Optional
from app.llm.base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    """Adapter for Google Gemini API."""
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self._genai = None

    def _get_genai(self):
        if self._genai is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run 'pip install google-generativeai'")
        return self._genai

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.0
    ) -> str:
        genai = self._get_genai()
        generation_config = {"temperature": temperature}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        system_instruction = system_prompt if system_prompt else None
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction,
            generation_config=generation_config
        )
        response = model.generate_content(prompt)
        return response.text or ""
