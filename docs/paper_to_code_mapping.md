# Paper-to-Code Mapping: Datrics Text2SQL (arXiv:2506.12234v1)

This document provides a line-by-line, module-by-module mapping between the concepts, equations, and algorithms described in the research paper **“Datrics Text2SQL: A Framework for Natural Language to SQL Query Generation”** (Gladkykh & Kirykov, Datrics, March 2025) and their corresponding implementations in this repository.

---

## 1. Paper Overview & Architectural Modules

The Datrics Text2SQL architecture consists of 8 primary modules ($A$ through $H$), progressing through database schema understanding, progressive example retrieval, multi-representation table retrieval, domain table refinement, adaptive generation, AST validation, and bounded self-correction.

```
       [Database Schema]               [Q-SQL Training Examples]
               │                                   │
               ▼                                   ▼
      Module A: Doc Generation             Module B: KB Indexing
  (TableDocGenerator, Entity Voting)     (7-Vector Cloud Ak, ChromaDB)
               │                                   │
               └──────────────┬────────────────────┘
                              ▼
                     [User Query (raw)]
                              │
                              ▼
                 Module C: Query Understanding
              (Nk, Mk, M'k, Ek, Ambiguity Checks)
                              │
                              ▼
             Module D: Progressive Example Retrieval
         (5 Cascading Stages with Sim = (cosθ+1)/2)
                              │
               ┌──────────────┴──────────────┐
               │                             │
    Stage 1 Exact Match             Stage 2-5 Fallback
               │                             │
               │                             ▼
               │                Module E: Table Retrieval
               │                  (6 Queries Z1 to Z6)
               │                             │
               │                             ▼
               │                Module F: Table Refinement
               │            (TB = LLM(N,R), TR = LLM(N,Instr,R))
               │                             │
               └──────────────┬──────────────┘
                              ▼
                 Module G: SQL Generation
               (Direct, Exact, Aligned, Template)
                              │
                              ▼
            Module H: AST Validation & Safe Execution
           (sqlglot read-only AST, sqlite mode=ro URI)
                              │
                              ▼
                      [Bounded Repair Loop]
```

---

## 2. Module Traceability Matrix

### Module A: Schema Understanding & Documentation Generation
* **Paper Section**: Section II.A, Pages 3–7
* **Key Concepts**:
  * Multi-aspect table documentation: `name`, `summary`, `purpose`, `dependencies_thoughts`, `keys`, `connected_tables`, `columns`, `entities`, `strong_entities`.
  * Repeated generation with frequency voting (Paper p. 4–6): multiple LLM passes filter out one-off hallucinated entities and promote stable concepts into `strong_entities`.
* **Implementation Files**:
  * Schemas: [`app/schemas/documentation.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/schemas/documentation.py)
  * Introspection: [`app/database/introspection.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/database/introspection.py)
  * Doc Generator: [`app/ingestion/doc_generator.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/ingestion/doc_generator.py)
  * Frequency Voting: [`app/ingestion/entity_voting.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/ingestion/entity_voting.py)
  * Persisted Documentation: [`data/table_docs.json`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/data/table_docs.json)

---

### Module B: Question-SQL Knowledge Base Indexing
* **Paper Section**: Section II.B, Pages 10–12
* **Key Concepts**:
  * Example representation tuple: $A_k = (I_k, S_{code_k}, N_k, M_k, M'_k, \mathcal{E}_k, V_k, O_k)$
  * Paraphrasing enricher generating 3 variations per question ($V_k$).
  * Total of 7 vector representations stored in ChromaDB for high-recall cosine matching.
* **Implementation Files**:
  * Example Schema: [`app/schemas/example.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/schemas/example.py)
  * Enricher: [`app/ingestion/example_enricher.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/ingestion/example_enricher.py)
  * Indexing Pipeline: [`app/knowledge_base/indexing_pipeline.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/knowledge_base/indexing_pipeline.py)
  * Vector Store: [`app/knowledge_base/vector_store.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/knowledge_base/vector_store.py)

---

### Module C: Query Understanding & Normalization
* **Paper Section**: Section II.C, Pages 8–10
* **Key Concepts**:
  * Raw question decomposition into normalized intent $N_k$, main clause $M_k$, details $M'_k$, and extracted entities $\mathcal{E}_k$.
  * Early ambiguity detection and unsupported query flagging with user clarification messaging.
* **Implementation Files**:
  * Schema: [`app/schemas/query_understanding.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/schemas/query_understanding.py)
  * Analyzer: [`app/query_understanding/analyzer.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/query_understanding/analyzer.py)

---

### Module D: Progressive Example Retrieval
* **Paper Section**: Section II.D, Pages 16–21
* **Key Formula**: Cosine similarity normalized to $[0, 1]$:
  $$\text{Sim}(X, Y_i) = \frac{\cos(\theta) + 1}{2} = \frac{X \cdot Y_i + \|X\| \|Y_i\|}{2 \|X\| \|Y_i\|}$$
* **5 Cascading Stages**:
  1. **Stage 1 (Exact Match)**: $\text{Sim}(I, I_k) \to 1.0$ (direct SQL output bypass).
  2. **Stage 2 (Normalized Match)**: $\text{Sim}(N, N_k) \ge P_{95}$ ($0.92$).
  3. **Stage 3 (Main Clause Match)**: $\text{Sim}(N \cup M, N_k \cup M_k) \ge P_{99}$ ($0.88$).
  4. **Stage 4 (Expanded Representation)**: Search across all representations with $P_{01}$ ($0.75$).
  5. **Stage 5 (Reranking / Fallback)**: Cross-encoder ranking with threshold $\tau'$.
* **Implementation Files**:
  * Progressive Retriever: [`app/retrieval/progressive_example.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/retrieval/progressive_example.py)
  * Similarity Service: [`app/embeddings/sentence_transformer.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/embeddings/sentence_transformer.py)
  * Cross-Encoder Reranker: [`app/retrieval/reranker.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/retrieval/reranker.py)

---

### Module E: Multi-Representation Table Retrieval ($Z_1 \dots Z_6$)
* **Paper Section**: Section II.E, Pages 22–23
* **The 6 Exact Queries**:
  * $Z_1$: Main clause $M$ queried against `description` and `entity` categories.
  * $Z_2$: Normalized question $N$ queried against `description` and `entity` categories.
  * $Z_3$: Extracted concepts $\mathcal{E}$ queried against `connected_tables` and `entity` categories.
  * $Z_4$: Main clause $M$ queried against `table_name` category.
  * $Z_5$: Normalized question $N$ queried against `table_name` category.
  * $Z_6$: Extracted concepts $\mathcal{E}$ queried against `table_name` category.
* **Implementation Files**:
  * Retriever: [`app/retrieval/table_retrieval.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/retrieval/table_retrieval.py)

---

### Module F: Domain-Specific Table Refinement
* **Paper Section**: Section II.F, Pages 24–25
* **Two-Stage Refinement Formulation**:
  1. $T_B = \text{LLM}(N, R)$: detect required tables from business rules $R$.
  2. Candidate union: $T_{\text{total}} = T_{\text{det}} \cup T_B$, full pool: $T_{\text{total}} \cup T_{\text{code}}$.
  3. $T_R = \text{LLM}(N, \text{Instr\_Domain}, R, T_{\text{total}} \cup T_{\text{code}})$: final reasoning-based table selection with join coverage analysis.
* **Implementation Files**:
  * Refiner: [`app/table_refinement/refiner.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/table_refinement/refiner.py)
  * Domain Instructions: [`app/knowledge_base/domain_rules.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/knowledge_base/domain_rules.py)
  * Rules Data: [`data/business_rules.json`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/data/business_rules.json)

---

### Module G: Adaptive SQL Generation Strategies
* **Paper Section**: Section II.G, Pages 25–27
* **4 Supported Strategies**:
  * `DIRECT_OUTPUT` ($S_{\text{sql}}^R$): Direct execution of verified stored SQL query.
  * `EXACT_EXAMPLE` ($S_{\text{code}}^{**}$): SQL generated by adapting an exact normalized structural match.
  * `STRONGLY_ALIGNED` ($S_{\text{code}}^*$): SQL generated using relevant examples and refined candidate schema.
  * `FLEXIBLE_TEMPLATE` ($S_{\text{code}} + T_R$): Schema-driven generation guided by table documentation and business rules.
* **Implementation Files**:
  * Strategy Selector: [`app/sql_generation/strategies.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/sql_generation/strategies.py)
  * Generator: [`app/sql_generation/generator.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/sql_generation/generator.py)

---

### Module H: AST SQL Validation, Safe Execution & Error Repair
* **Paper Section**: Section II.H, Page 28
* **Safety & Repair Boundary**:
  * Strict AST parsing using `sqlglot` (read-only `SELECT` enforcement; blocking `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `PRAGMA`).
  * Non-existent table/column identifier rejection against known schema.
  * Multi-statement semicolon prevention.
  * Read-only SQLite URI (`file:///...?mode=ro` and `PRAGMA query_only = ON`).
  * Bounded retry loop (`MAX_SQL_CORRECTION_ATTEMPTS = 2`) feeding syntax or runtime error messages back into the generator prompt.
* **Implementation Files**:
  * AST Validator: [`app/sql_validation/validator.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/sql_validation/validator.py)
  * Safe Executor: [`app/sql_validation/executor.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/sql_validation/executor.py)
  * Connection Manager: [`app/database/connection.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/database/connection.py)
  * Orchestrator Loop: [`app/pipeline.py`](file:///c:/Users/moham/OneDrive/Desktop/another%20paper/app/pipeline.py)
