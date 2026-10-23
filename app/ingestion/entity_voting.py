from typing import List, Dict, Tuple, Optional
from collections import Counter
import json
import re
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.config import settings

class EntityVotingExtractor:
    """
    Module B / Paper p. 4-6: Repeated Generation & Frequency-Based Voting Strategy.
    Runs multiple LLM passes (n rounds) for the same input documentation,
    tallies concept frequencies, filters out one-off anomalous entities,
    and identifies 'strong_entities' (frequency >= min_frequency).
    """
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def extract_with_voting(
        self,
        table_name: str,
        table_summary: str,
        columns_text: str,
        rounds: Optional[int] = None,
        min_frequency: Optional[int] = None
    ) -> Tuple[List[str], List[str]]:
        n_rounds = rounds or settings.ENTITY_VOTING_ROUNDS
        threshold = min_frequency or settings.ENTITY_VOTING_MIN_FREQUENCY

        prompt = f"""
Extract meaningful business entities and concepts that are represented or inferred from this table.
Table Name: {table_name}
Summary: {table_summary}
Columns: {columns_text}

Return ONLY a JSON array of concept strings:
["entity1", "entity2", "entity3"]
"""
        all_candidates: List[str] = []

        for r in range(n_rounds):
            # Non-zero temperature to sample diverse representations across runs
            temp = 0.4 if n_rounds > 1 else 0.0
            response = self.llm.generate(prompt=prompt, json_mode=True, temperature=temp)
            try:
                cleaned = re.sub(r"^```json\s*", "", response.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
                concepts = json.loads(cleaned)
                if isinstance(concepts, list):
                    for c in concepts:
                        norm_c = str(c).strip().lower()
                        if norm_c:
                            all_candidates.append(norm_c)
            except Exception:
                continue

        if not all_candidates:
            # Fallback based on table name and columns
            base_concepts = [table_name.lower()] + [c.lower() for c in columns_text.split() if len(c) > 3][:4]
            return base_concepts, [table_name.lower()]

        counts = Counter(all_candidates)
        # All entities that appeared more than once, or all if single round
        all_unique = sorted(list(counts.keys()))

        if n_rounds > 1:
            # Paper p. 6: "Those entities occur just once within the series of LLM calls and are considered insignificant"
            strong_entities = [concept for concept, count in counts.items() if count >= threshold]
            # If none met threshold, take top occurring
            if not strong_entities and counts:
                strong_entities = [counts.most_common(1)[0][0]]
        else:
            strong_entities = all_unique[:3]

        return all_unique, strong_entities
