import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.config import settings
from app.schemas.documentation import TableDocumentation
from app.schemas.example import NormalizedExample, ExtractedEntity, QueryOperation
from app.knowledge_base.vector_store import VectorStoreManager
from app.knowledge_base.domain_rules import DomainRulesExtractor
from app.ingestion.example_enricher import ExampleEnricher

class IndexingPipeline:
    """
    Module B: Knowledge-Base Indexing Pipeline.
    Idempotent pipeline indexing:
    1. Table documentation across 5 representation categories (description, connected_tables, table_name, entity, full)
    2. Question-SQL examples across 7 vector representations (initial, 3 variations, normalized, main clause, entities)
    3. Domain-specific rules and instructions (Instr_Domain)
    """
    def __init__(
        self,
        vector_store: Optional[VectorStoreManager] = None,
        data_dir: Optional[str] = None
    ):
        self.vector_store = vector_store or VectorStoreManager()
        self.data_dir = Path(data_dir or (Path(__file__).resolve().parent.parent.parent / "data"))
        self.enricher = ExampleEnricher()
        self.domain_extractor = DomainRulesExtractor()

        self.table_docs: Dict[str, TableDocumentation] = {}
        self.train_examples: Dict[str, NormalizedExample] = {}
        self.business_rules: List[Dict[str, Any]] = []
        self.domain_instructions: str = ""

    def load_data_files(self):
        # Load Table Documentation
        docs_file = self.data_dir / "table_docs.json"
        if docs_file.exists():
            with open(docs_file, "r", encoding="utf-8") as f:
                raw_docs = json.load(f)
                for tbl, d in raw_docs.items():
                    self.table_docs[tbl] = TableDocumentation(**d)

        # Load Business Rules
        rules_file = self.data_dir / "business_rules.json"
        if rules_file.exists():
            with open(rules_file, "r", encoding="utf-8") as f:
                self.business_rules = json.load(f)

        # Load Training Examples
        examples_file = self.data_dir / "train_examples.json"
        if examples_file.exists():
            with open(examples_file, "r", encoding="utf-8") as f:
                raw_examples = json.load(f)
                for ex in raw_examples:
                    entities = [
                        ExtractedEntity(
                            label=e.get("label", ""),
                            entity_type=e.get("entity_type", "category"),
                            attributes=e.get("attributes")
                        )
                        for e in ex.get("entities", [])
                    ]
                    operations = [
                        QueryOperation(
                            operation=o.get("operation", "SELECT"),
                            target=o.get("target", "*"),
                            condition=o.get("condition")
                        )
                        for o in ex.get("operations", [])
                    ]
                    ex_obj = NormalizedExample(
                        id=ex["id"],
                        question=ex["question"],
                        sql=ex["sql"],
                        normalized_question=ex["normalized_question"],
                        main_clause=ex["main_clause"],
                        details=ex.get("details", ""),
                        entities=entities,
                        tables=ex.get("tables", []),
                        columns=ex.get("columns", []),
                        operations=operations,
                        variations=ex.get("variations", [])
                    )
                    self.train_examples[ex["id"]] = ex_obj

    def index_all(self):
        """Executes full idempotent indexing."""
        self.load_data_files()
        self.index_table_docs()
        self.index_examples()
        domain_res = self.domain_extractor.extract_from_examples(
            list(self.train_examples.values()),
            self.business_rules
        )
        self.domain_instructions = domain_res.instructions_text
        return {
            "indexed_tables": len(self.table_docs),
            "indexed_examples": len(self.train_examples),
            "business_rules_count": len(self.business_rules)
        }

    def index_table_docs(self):
        """
        Indexes table documentation across multiple categories matching paper p. 7-8:
        1. Full documentation
        2. Dependencies & connected tables
        3. Table metadata (names & keys)
        4. Entity relationships
        """
        for tbl_name, doc in self.table_docs.items():
            base_meta = {
                "table_name": tbl_name,
                "dependencies": doc.dependencies_thoughts,
                "connected_tables": doc.connected_tables,
                "keys": doc.keys
            }

            # 1. Description category
            desc_text = f"Table {tbl_name}: {doc.summary}. Purpose: {doc.purpose}"
            self.vector_store.upsert_table_documentation(
                doc_id=f"doc_{tbl_name}_desc",
                text=desc_text,
                metadata={**base_meta, "category": "description"}
            )

            # 2. Table Name category
            self.vector_store.upsert_table_documentation(
                doc_id=f"doc_{tbl_name}_name",
                text=f"{tbl_name} table",
                metadata={**base_meta, "category": "table_name"}
            )

            # 3. Connected Tables & Dependencies
            conn_text = f"Connected tables for {tbl_name}: {', '.join(doc.connected_tables)}. Dependencies: {doc.dependencies_thoughts}"
            self.vector_store.upsert_table_documentation(
                doc_id=f"doc_{tbl_name}_conn",
                text=conn_text,
                metadata={**base_meta, "category": "connected_tables"}
            )

            # 4. Entity Category
            entity_text = f"Entities for {tbl_name}: {', '.join(doc.entities + doc.strong_entities)}"
            self.vector_store.upsert_table_documentation(
                doc_id=f"doc_{tbl_name}_entities",
                text=entity_text,
                metadata={**base_meta, "category": "entity"}
            )

    def index_examples(self):
        """
        Indexes Q-SQL examples across 7 vector representations matching paper p. 11-12.
        """
        for ex_id, ex in self.train_examples.items():
            base_meta = {
                "example_id": ex_id,
                "sql": ex.sql,
                "tables": ex.tables,
                "columns": ex.columns,
                "initial_question": ex.question,
                "normalized_question": ex.normalized_question,
                "main_clause": ex.main_clause
            }

            # 1. Initial Question
            self.vector_store.upsert_query_example(
                entry_id=f"{ex_id}_init",
                text=ex.question,
                metadata={**base_meta, "representation_type": "initial_question"}
            )

            # 2. Normalized Question
            self.vector_store.upsert_query_example(
                entry_id=f"{ex_id}_norm",
                text=ex.normalized_question,
                metadata={**base_meta, "representation_type": "normalized_question"}
            )

            # 3. Main Clause
            self.vector_store.upsert_query_example(
                entry_id=f"{ex_id}_main",
                text=ex.main_clause,
                metadata={**base_meta, "representation_type": "main_clause"}
            )

            # 4. Extracted Entities
            entity_str = " ".join([e.label for e in ex.entities])
            if entity_str:
                self.vector_store.upsert_query_example(
                    entry_id=f"{ex_id}_entities",
                    text=entity_str,
                    metadata={**base_meta, "representation_type": "entities"}
                )

            # 5, 6, 7. Variations (ensure 3 variations exist)
            variations = ex.variations
            if not variations or len(variations) < 3:
                variations = self.enricher.generate_variations(
                    question=ex.question,
                    normalized_question=ex.normalized_question,
                    sql=ex.sql,
                    count=3
                )
                ex.variations = variations

            for v_idx, var_text in enumerate(variations[:3], 1):
                self.vector_store.upsert_query_example(
                    entry_id=f"{ex_id}_var_{v_idx}",
                    text=var_text,
                    metadata={**base_meta, "representation_type": f"variation_{v_idx}"}
                )
