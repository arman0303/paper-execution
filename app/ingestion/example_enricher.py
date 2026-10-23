import json
import re
from typing import List, Optional
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.config import settings

class ExampleEnricher:
    """
    Paper Section III (p. 11-12): Generates 3 paraphrased question variations
    per normalized example to create a diverse cloud of embeddings.
    """
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def generate_variations(
        self,
        question: str,
        normalized_question: str,
        sql: str,
        count: Optional[int] = None
    ) -> List[str]:
        n = count or settings.PARAPHRASE_COUNT
        prompt = f"""
Generate {n} diverse natural-language question variations for the following query and SQL answer.
Ensure phrasing differs in vocabulary, word order, and style, while maintaining the exact same query intent.

Original Question: "{question}"
Normalized Intent: "{normalized_question}"
SQL Code: "{sql}"

Return ONLY a JSON array of {n} strings:
["variation 1", "variation 2", "variation 3"]
"""
        response = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.5)
        try:
            cleaned = re.sub(r"^```json\s*", "", response.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            variations = json.loads(cleaned)
            if isinstance(variations, list) and len(variations) > 0:
                return [str(v).strip() for v in variations[:n]]
        except Exception:
            pass

        # Fallback paraphrases
        return [
            f"Please {question.lower()}",
            f"Query records to {normalized_question.lower()}",
            f"Retrieve data: {question}"
        ]
