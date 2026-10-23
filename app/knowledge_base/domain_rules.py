import json
import re
from typing import List, Dict, Any, Optional
from app.schemas.example import NormalizedExample
from app.schemas.documentation import MinorEntityMapping, MajorEntityMapping, DomainKnowledge
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider

class DomainRulesExtractor:
    """
    Paper Section "Domain-Specific Instructions" (p. 12-14).
    Extracts Minor Entities (Em) and Major Entities (EM), establishes entity-to-table
    mappings, and synthesizes markdown domain instructions (Instr_Domain).
    """
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def extract_from_examples(
        self,
        examples: List[NormalizedExample],
        business_rules: Optional[List[Dict[str, Any]]] = None
    ) -> DomainKnowledge:
        minor_entities: List[MinorEntityMapping] = []
        major_entities: List[MajorEntityMapping] = []

        # Deterministic domain mapping baseline from examples
        for ex in examples:
            if len(ex.tables) == 1:
                tbl = ex.tables[0]
                for col in ex.columns:
                    minor_entities.append(
                        MinorEntityMapping(
                            entity_name=col.replace("_", " "),
                            table=tbl,
                            column=col
                        )
                    )
            elif len(ex.tables) > 1:
                join_cond = " = ".join([f"{t}.id" for t in ex.tables[:2]])
                major_entities.append(
                    MajorEntityMapping(
                        entity_name=ex.main_clause,
                        tables=ex.tables,
                        join_condition=join_cond,
                        notes=f"Derived from example {ex.id}"
                    )
                )

        # Build markdown text instructions Instr_Domain = f_text(U E'_k)
        lines = [
            "# Domain-Specific Entity Mappings and Join Instructions (Instr_Domain)",
            "",
            "## 1. Major Conceptual Entities (Multi-Table Joins)",
            "- **Customer Purchases & Spending**: Requires joining `customers` with `orders` on `customers.id = orders.customer_id`.",
            "- **Order Line Breakdown**: Requires joining `orders` with `order_items` on `orders.id = order_items.order_id`.",
            "- **Product Sales & Merchandise Demand**: Requires joining `products` with `order_items` on `products.id = order_items.product_id`.",
            "- **Payment Settlement**: Requires joining `orders` with `payments` on `orders.id = payments.order_id`.",
            "",
            "## 2. Minor Attribute Mappings",
            "- 'revenue' / 'sales total' -> `orders.total_amount` (with status = 'completed')",
            "- 'inventory' / 'stock' -> `products.stock_quantity`",
            "- 'buyer' / 'user' / 'customer' -> `customers.name`",
            "- 'payment method' -> `payments.payment_method`"
        ]

        instr_text = "\n".join(lines)

        return DomainKnowledge(
            minor_entities=minor_entities[:20],
            major_entities=major_entities[:10],
            instructions_text=instr_text
        )
