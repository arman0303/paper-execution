# Datrics Text2SQL Implementation (arXiv:2506.12234v1)

> **Research Paper**: *“Datrics Text2SQL: A Framework for Natural Language to SQL Query Generation”*  
> **Authors**: Tetiana Gladkykh & Kyrylo Kirykov (Datrics, March 2025) — [arXiv:2506.12234v1](https://arxiv.org/abs/2506.12234)

A modular, production-ready, locally runnable implementation of the **Datrics Text2SQL** architecture. Designed for Computer Science students, AI/ML researchers, and backend engineers, this project demonstrates how to build a Retrieval-Augmented Generation (RAG) system specialized for translating natural language questions into accurate, secure SQL statements.

---

## 🌟 Architecture & Key Highlights

The Datrics Text2SQL framework solves three core challenges in enterprise text-to-SQL: **linguistic ambiguity**, **domain terminology**, and **complex relational schemas**.

1. **Multi-Aspect Table Documentation**: Ingests database schemas and builds structured JSON documentation (`name`, `summary`, `purpose`, `dependencies_thoughts`, `keys`, `connected_tables`, `columns`, `entities`, `strong_entities`).
2. **Frequency-Based Entity Voting**: Samples multiple LLM concept extraction passes to promote robust concepts to `strong_entities` and discard anomalous one-off terms.
3. **Multi-Vector Q-SQL Example Cloud**: Normalizes examples into $A_k = (I_k, S_{code_k}, N_k, M_k, M'_k, \mathcal{E}_k, V_k, O_k)$ and enriches each with 3 question variations (producing 7 vector representations stored in ChromaDB).
4. **Progressive Example Retrieval**: Uses the paper's cosine similarity scaling $\text{Sim}(X, Y) = \frac{\cos(\theta) + 1}{2} \in [0, 1]$ across 5 cascading stages (Exact Match $\to$ Normalized $P_{95} \to$ Main Clause $P_{99} \to$ Expanded $P_{01} \to$ Cross-Encoder Reranker).
5. **Multi-Representation Table Retrieval ($Z_1 \dots Z_6$)**: Executes 6 targeted queries with metadata filters against ChromaDB, deduplicating candidate tables.
6. **Two-Stage Table Refinement**: Combines business rules detection ($T_B = \text{LLM}(N, R)$) and reasoning-based join planning ($T_R = \text{LLM}(N, \text{Instr\_Domain}, R, T_{\text{total}} \cup T_{\text{code}})$).
7. **Adaptive SQL Generation Strategies**: Dynamically routes to Direct Output, Exact Example, Strongly Aligned, or Flexible Template-based generation.
8. **AST Validation & Read-Only Security Boundary**: Enforces read-only SELECT queries with `sqlglot`, prevents injections/mutations, verifies identifiers against the schema, and bounds self-correction attempts.

---

## 🗂️ Project Structure

```text
Paper/
├── .env.example                     # Sample environment settings
├── .gitignore                       # Git exclusion rules
├── requirements.txt                 # Python dependencies
├── README.md                        # Documentation and guide
├── TODO.md                          # Implementation roadmap
├── docs/
│   ├── architecture.md              # Detailed architecture diagram and workflow
│   └── paper_mapping.md             # Line-by-line paper section mapping
├── data/
│   ├── sample_ecommerce.db          # Seeded SQLite test database
│   ├── schema.sql                   # Relational DDL (customers, products, orders, etc.)
│   ├── seed_data.py                 # Reproducible database seed script
│   ├── table_docs.json              # Structured table documentation matching paper format
│   ├── business_rules.json          # Domain rules (R) for order status and revenue
│   ├── train_examples.json          # 22 curated Q-SQL training examples with variations
│   ├── test_examples.json           # 10 held-out evaluation test cases
│   └── evaluation_results.json      # Machine-readable evaluation benchmark results
├── app/
│   ├── config.py                    # Pydantic Settings configuration manager
│   ├── pipeline.py                  # Master End-to-End Orchestrator
│   ├── schemas/                     # Strongly typed Pydantic models
│   │   ├── documentation.py
│   │   ├── example.py
│   │   ├── query_understanding.py
│   │   ├── retrieval.py
│   │   └── sql.py
│   ├── database/                    # Connection & Introspection
│   │   ├── connection.py            # Read-only SQLite connection manager
│   │   └── introspection.py         # Deterministic schema introspector
│   ├── ingestion/                   # Documentation & Entity Voting
│   │   ├── doc_generator.py
│   │   ├── entity_voting.py         # Multi-run frequency voting
│   │   └── example_enricher.py      # Question paraphrasing generator
│   ├── knowledge_base/              # Vector DB & Domain Mappings
│   │   ├── vector_store.py          # ChromaDB multi-category store with fallback
│   │   ├── indexing_pipeline.py     # Idempotent indexing manager
│   │   └── domain_rules.py          # Instr_Domain and Minor/Major entity derivation
│   ├── query_understanding/         # Module C Analyzer
│   │   └── analyzer.py              # Normalization (Nk), Main Clause (Mk), Ambiguity check
│   ├── retrieval/                   # Modules D & E Retrievers
│   │   ├── progressive_example.py   # Cascading progressive threshold retriever
│   │   ├── table_retrieval.py       # 6-query multi-aspect table retriever (Z1..Z6)
│   │   └── reranker.py              # Cross-Encoder Quora duplicate question reranker
│   ├── table_refinement/            # Module F Refinement
│   │   └── refiner.py               # TB = LLM(N, R) & TR = LLM(N, Instr_Domain, R, Candidates)
│   ├── sql_generation/              # Module G Generation
│   │   ├── strategies.py            # Strategy selector
│   │   └── generator.py             # Schema & template prompt synthesizer
│   ├── sql_validation/              # Module H Validation & Execution
│   │   ├── validator.py             # sqlglot AST read-only security boundary
│   │   └── executor.py              # Safe SQLite execution engine with timeouts
│   ├── api/                         # FastAPI REST Endpoints
│   │   └── main.py
│   ├── ui/                          # Streamlit Web App
│   │   └── streamlit_app.py
│   └── evaluation/                  # Reproducibility & Benchmark Runner
│       ├── baseline.py              # Schema-only baseline without retrieval
│       ├── metrics.py               # Exact match, execution accuracy, table precision/recall
│       └── runner.py                # Benchmark script comparing Datrics vs Baseline
└── tests/                           # Pytest unit & integration test suite (16 tests)
    ├── conftest.py
    ├── test_database.py
    ├── test_sql_validation.py
    ├── test_query_understanding.py
    ├── test_retrieval.py
    └── test_end_to_end.py
```

---

## 🚀 Setup & Execution Guide (Windows 11 / PowerShell)

### Step 1: Open PowerShell in the project directory
```powershell
cd "c:\Users\moham\OneDrive\Desktop\Paper"
```

### Step 2: Configure Environment
Copy the example environment configuration:
```powershell
Copy-Item .env.example .env
```
*(By default, `LLM_PROVIDER=mock` is enabled for instant offline execution and 100% reproducible tests without requiring an external paid API key. To use OpenAI or Google Gemini, simply edit `.env` and insert your API key).*

### Step 3: Seed the Database
Initialize and seed the SQLite database with realistic e-commerce data:
```powershell
python data/seed_data.py
```

### Step 4: Run the Automated Unit Test Suite
Run all 16 test cases covering database isolation, AST safety, query understanding, progressive retrieval, and end-to-end execution:
```powershell
python -m pytest tests/ -v
```

### Step 5: Run the Evaluation Benchmark
Run the reproducible benchmark comparing the Datrics Text2SQL pipeline against the schema-only baseline:
```powershell
python -m app.evaluation.runner
```

### Step 6: Launch the Streamlit Web Application
Run the interactive user interface:
```powershell
streamlit run app/ui/streamlit_app.py
```
Open your browser to `http://localhost:8501`.

### Step 7: (Optional) Run the FastAPI REST Server
```powershell
uvicorn app.api.main:app --reload --port 8000
```
API documentation is automatically available at `http://localhost:8000/docs`.

---

## 🔬 Benchmark Results

The evaluation runner tests 10 held-out cases that cover filtering, multi-table joins, aggregations, and ambiguous/unsupported requests:

| Metric | Datrics Text2SQL (arXiv:2506.12234v1) | Baseline (Schema-Only) |
| :--- | :---: | :---: |
| **Execution Accuracy** | **100.0%** (7/7 evaluable) | 100.0% |
| **Exact SQL Match Rate** | **100.0%** (7/7 evaluable) | 100.0% |
| **Table Selection Precision** | **1.00** | 1.00 |
| **Table Selection Recall** | **1.00** | 1.00 |
| **Ambiguity & Clarification Rate** | **30.0%** (3/10 safely flagged) | 0.0% (Unsafe / Hallucinated) |
| **Average Query Latency** | ~70 ms | < 1 ms |

> **Disclaimer**: This is a prototype empirical comparison evaluated on our curated held-out test suite. The original research paper does not publish numerical benchmark comparisons against standard datasets (e.g., Spider or BIRD).

---

## 💡 Beginner-Friendly Concept Guide

- **What is Text-to-SQL?**: Converting human natural language ("How much money did we make in May?") into database query code (`SELECT SUM(total_amount) FROM orders WHERE order_date >= '2024-05-01' AND ...`).
- **Why RAG for SQL?**: Raw LLMs hallucinate non-existent table names, confuse column names, or forget critical business filters (like ignoring cancelled orders). Retrieval-Augmented Generation feeds the model only the verified schema and matching SQL patterns it needs.
- **What is Progressive Retrieval?**: Rather than a static search, the system checks in stages: first looking for an exact match, then searching by normalized intent, then searching by main clause, and finally falling back to broader candidate retrieval.
- **Why AST Validation?**: We never trust an LLM prompt to keep a database safe. We parse the query syntax tree (using `sqlglot`) to guarantee it is strictly a read-only `SELECT` query, blocking destructive statements like `DROP` or `DELETE` at the parser level.

---

## 📋 Paper Component Checklist

- [x] **Table Documentation Schema**: Full JSON schema with dependencies, keys, and connected tables (`app/schemas/documentation.py`).
- [x] **Entity Voting Strategy**: Multi-run LLM generation and frequency thresholding for strong entities (`app/ingestion/entity_voting.py`).
- [x] **Example Normalization**: Structured $A_k = (I_k, S_{code_k}, N_k, M_k, M'_k, \mathcal{E}_k, V_k, O_k)$ extraction (`app/query_understanding/analyzer.py`).
- [x] **Question Variations**: 3 generated paraphrases per example yielding 7 embeddings (`app/ingestion/example_enricher.py`).
- [x] **Multi-Category Vector Indexing**: Stored in ChromaDB with category metadata (`app/knowledge_base/indexing_pipeline.py`).
- [x] **Progressive Example Retrieval**: 5-stage cascading thresholds with $\text{Sim} = \frac{\cos(\theta)+1}{2}$ (`app/retrieval/progressive_example.py`).
- [x] **Cross-Encoder Reranking**: Optional Quora/MS-Marco cross-encoder adapter (`app/retrieval/reranker.py`).
- [x] **Multi-Aspect Table Retrieval**: The 6 exact queries $Z_1 \dots Z_6$ with metadata filters (`app/retrieval/table_retrieval.py`).
- [x] **Business-Rule & LLM Refinement**: $T_B = \text{LLM}(N, R)$ and $T_R = \text{LLM}(N, \text{Instr\_Domain}, R, \text{Candidates})$ (`app/table_refinement/refiner.py`).
- [x] **SQL Generation Strategies**: Direct, Exact Example, Strongly Aligned, Flexible Template (`app/sql_generation/generator.py`).
- [x] **SQL AST Validation & Safe Execution**: Read-only SQLite URI, statement validation, and bounded repair loop (`app/sql_validation/`).
- [x] **Streamlit UI**: Full query generator, schema inspector, example browser, and diagnostic trace viewer (`app/ui/streamlit_app.py`).
- [x] **Empirical Evaluation**: Benchmark script comparing pipeline against schema-only baseline with metrics (`app/evaluation/runner.py`).
