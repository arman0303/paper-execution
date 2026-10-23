# Paper to Code Implementation Mapping

This document provides a line-by-line mapping between the concepts, equations, and sections of the paper **“Datrics Text2SQL: A Framework for Natural Language to SQL Query Generation” (arXiv:2506.12234v1)** and the concrete codebase implementation.

---

## 1. Table Documentation Structure

### Paper Reference (Page 3-4, Section: "Train based on Documentation")
The paper specifies:
- `name`: The table's name
- `summary`: A brief description of what the table contains
- `purpose`: Explains the table's role and why it exists
- `dependencies_thoughts`: Informal notes on relationships between this table's fields and fields in other tables
- `keys`: A list of key columns used to join or relate to other tables
- `connected_tables`: An array of related table names
- `columns`: Array of `{column, description}`
- `entities`: Key concepts extracted from documentation
- `strong_entities`: Significant subset derived via voting strategy

### Implementation
- `app/schemas/documentation.py`: `TableColumnDoc`, `TableDocumentation`
- `app/ingestion/doc_generator.py`: Generates these fields via prompt or schema inspection
- `app/ingestion/entity_voting.py`: Repeated generation and frequency voting

---

## 2. Repeated Generation and Voting Strategy

### Paper Reference (Page 4-6, Section: "I. Documents Processing")
*"we generate several LLM responses for the same input content and assess the frequency of the concept occurrence within multiple runs. This allows extracting the strong entities from the entities' list... Those entities occur just once within the series of LLM calls and are considered insignificant."*

### Implementation
- `app/ingestion/entity_voting.py`:
  - `extract_entities_with_voting(doc_text, rounds=3, min_frequency=2)`: Runs multiple sampling steps, collects candidate entity terms, tallies frequencies, and promotes concepts with occurrences $\ge \text{min\_frequency}$ to `strong_entities`.

---

## 3. Question-SQL Example Structuring

### Paper Reference (Page 9-10, Section: "I. Example Normalization and Structuring")
Formula:
$$A_k = (I_k, S_{code_k}, N_k, M_k, \mathcal{E}_k, V_k, O_k)$$
where:
- $I_k$: Initial user query
- $S_{code_k}$: Corresponding SQL query
- $N_k$: Normalized form (database names stripped, display words removed, generalized time/numbers)
- $M_k, M'_k$: Main clause vs details split
- $\mathcal{E}_k = \{(L_i, K_i, J_i)\}$: Entities with label $L$, type $K \in \{\text{category}, \text{metric}, \text{identifier}\}$, attributes $J$
- $V_k = \{T_{ik}, C_{ik}\}$: Data sources (tables and columns)
- $O = \{(\text{operation}, \text{target}, \text{condition})\}$: Aggregations, groupings, filters

### Implementation
- `app/schemas/example.py`: `ExtractedEntity`, `DataSourceReference`, `QueryOperation`, `NormalizedExample`
- `app/query_understanding/analyzer.py`: LLM prompt and regex post-processor implementing the exact normalization rules.

---

## 4. Example Enrichment with Question Variations

### Paper Reference (Page 11-12, Section: "III. Enrichment of the Example with the Variation of Question")
Generates 3 additional similar questions per example, yielding 7 embeddings:
1. Initial question ($I_k$)
2. Similar Question 1
3. Similar Question 2
4. Similar Question 3
5. Normalized Question ($N_k$)
6. Main Clause ($M_k$)
7. Extracted Entities ($\mathcal{E}_k$)

### Implementation
- `app/ingestion/example_enricher.py`: `generate_question_variations()`
- `app/knowledge_base/indexing_pipeline.py`: Ingests all 7 vector representations into ChromaDB with metadata tags `representation_type` and `example_id`.

---

## 5. Domain-Specific Instructions Extraction

### Paper Reference (Page 12-14, Section: "Domain-Specific Instructions")
- Table selection and justification: $\{T_{LLM_k}, W_{LLM_k}\} = LLM(I_k, \{T_{ik}\}, R, S_{code_k})$
- Entity classification:
  - Minor entities ($E_m$): Single column/attribute mappings
  - Major entities ($E_M$): Conceptual groupings requiring joins
- Instructions string: $Instr\_Domain = f_{text}(\bigcup E'_k)$

### Implementation
- `app/schemas/documentation.py`: `MinorEntityMapping`, `MajorEntityMapping`, `DomainKnowledge`
- `app/knowledge_base/domain_rules.py`: LLM-based entity extractor and synthesizer generating the markdown instruction bridge $Instr\_Domain$.

---

## 6. Progressive Example Retrieval

### Paper Reference (Page 16-21, Section: "Retrieve Appropriate Examples")
Similarity formula:
$$Sim(X, Y_i) = \frac{\cos(\theta) + 1}{2}$$
Four cascading stages:
- **Stage 1 (Exact Match):** $Sim(I, I_k) \ge \tau_{exact} \to S_{code}^R$ (Direct output SQL)
- **Stage 2 (Normalized Match):** $Sim(N, Q_k) \ge P_{95}^{SINT-N} \to S_{code}^{**}$ (Exact example-based)
- **Stage 3 (Main Clause Match):** $Sim(N, Q_k) \ge P_{99}^{SinterN \cup M} \to S_{code}^*$ (Strongly aligned example)
- **Stage 4 (Expanded Search):** $Sim(N, Q_k) \ge P_{01}^{Sintra} \to A'_{res}$
- **Stage 5 (Reranking):** Cross-encoder Quora/MS-Marco classifier $getRank(A_k) > \tau' \to S_{code}^*$, else template $S_{code}$.

### Implementation
- `app/retrieval/progressive_example.py`: `ProgressiveExampleRetriever` with explicit stage progression and threshold filters.
- `app/retrieval/reranker.py`: `CrossEncoderReranker` using HuggingFace sentence-transformers cross-encoder.

---

## 7. Multi-Representation Table Documentation Retrieval

### Paper Reference (Page 21-24, Section: "Retrieve Documentation on Related Tables")
6 queries against ChromaDB `table_docs` collection:
- $Z_1 = (M, \{\text{category} \in \{\text{description}, \text{entity}\}\}, n=10)$
- $Z_2 = (N, \{\text{category} \in \{\text{description}, \text{entity}\}\}, n=10)$
- $Z_3 = (E, \{\text{category} \in \{\text{connected\_tables}, \text{entity}\}\}, n=10)$
- $Z_4 = (M, \{\text{category} = \text{table\_name}\}, n=10)$
- $Z_5 = (N, \{\text{category} = \text{table\_name}\}, n=10)$
- $Z_6 = (E, \{\text{category} = \text{table\_name}\}, n=10)$

Union & Deduplicate: $Q_{unique} \to T_{det}$.
Business Rules table retrieval: $T_B = LLM(N, R)$.
Combined candidates: $T_{total} = T_{det} \cup T_B$.
Final Refinement: $T_R = LLM(N, Instr\_Domain, R, T_{total} \cup T_{code})$.

### Implementation
- `app/retrieval/table_retrieval.py`: `TableDocumentationRetriever`
- `app/table_refinement/refiner.py`: `TableRefiner` implementing $T_B$ and $T_R$.

---

## 8. SQL Code Generation Strategies

### Paper Reference (Page 26-27, Section: "SQL Code Generation")
- Strategy 1: Direct Output ($S_{code}^R$)
- Strategy 2: Exact Example-Based ($S_{code}^{**}$) + $T_{code}$ support
- Strategy 3: Strongly Aligned Example-Based ($S_{code}^*$) + $T_{code}$ balance
- Strategy 4: Flexible Template / Documentation-Driven ($S_{code} + T_R$)

### Implementation
- `app/sql_generation/strategies.py`: Enumeration and strategy router
- `app/sql_generation/generator.py`: Prompt builder with schema injection and example templates.

---

## 9. SQL Validation and Safe Execution

### Requirement (Module H)
- Read-only AST validation (prohibit mutations, DDL, PRAGMA, comments)
- Single SELECT / CTE statement verification
- Schema existence verification for tables and columns
- Read-only connection (`mode=ro`, `PRAGMA query_only = ON`)
- Timeout (5s) and row limit (100 rows)
- Bounded self-correction loop (max 2 attempts)

### Implementation
- `app/sql_validation/validator.py`: `SQLValidator` powered by `sqlglot`
- `app/sql_validation/executor.py`: `SafeSQLExecutor`
- `app/pipeline.py`: Coordinates generation -> validation -> execution -> self-correction.
