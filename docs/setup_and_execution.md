# Environment Setup & Execution Guide: Datrics Text2SQL

This document details how to install, configure, verify, execute, and benchmark the Datrics Text2SQL reproduction on Windows 11 (PowerShell) and Linux/macOS.

---

## 1. Prerequisites

* **Operating System**: Windows 10/11, macOS, or Linux.
* **Python**: Python 3.10 to 3.12 (Python 3.12 recommended).
* **Git**: Installed and configured with your GitHub credentials.

---

## 2. Step-by-Step Installation

### Clone the Repository
```powershell
git clone https://github.com/arman0303/another-paper.git
cd another-paper
```

### Create and Activate a Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(On macOS/Linux: `source .venv/bin/activate`)*

### Install Python Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configuration & Environment Variables

Copy the example environment configuration file:
```powershell
Copy-Item .env.example .env
```

Key configuration options in `.env`:

| Variable | Default Value | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` (deterministic, zero-cost, offline), `gemini`, or `openai` |
| `OPENAI_API_KEY` | *(empty)* | Required if `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Target OpenAI model |
| `GEMINI_API_KEY` | *(empty)* | Required if `LLM_PROVIDER=gemini` |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Target Gemini model |
| `EMBEDDING_PROVIDER` | `tfidf` | `sentence-transformers` (neural embeddings) or `tfidf` (fast offline fallback) |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_storage` | Local directory for persistent ChromaDB storage |
| `ENABLE_RERANKER` | `false` | Enable cross-encoder reranker in Stage 5 |
| `DATABASE_PATH` | `./data/sample_ecommerce.db`| SQLite database file path |
| `MAX_SQL_CORRECTION_ATTEMPTS` | `2` | Bounded repair attempts before failing |

---

## 4. Seeding the Relational Database

Create and populate the sample e-commerce SQLite database:
```powershell
python data/seed_data.py
```
This generates `data/sample_ecommerce.db` containing realistic tables (`customers`, `products`, `orders`, `order_items`, `payments`) with relational primary and foreign keys.

---

## 5. Running the Test Suite

Execute the 16 unit and integration test cases covering all architectural layers:
```powershell
python -m pytest tests/ -v
```

Verified test coverage includes:
* `test_readonly_connection_blocks_mutations`: Tests that read-only SQLite connections reject INSERT/UPDATE/DELETE.
* `test_schema_introspector_finds_tables`: Tests table and relationship discovery.
* `test_foreign_keys_correctly_detected`: Tests primary/foreign key constraint extraction.
* `test_paper_similarity_formula`: Validates normalized paper cosine formula $\text{Sim} = \frac{\cos\theta + 1}{2} \in [0, 1]$.
* `test_progressive_retriever_exact_match`: Tests direct SQL bypass on exact matches.
* `test_table_retriever_six_queries`: Tests $Z_1 \dots Z_6$ multi-aspect table retrieval.
* `test_valid_select_query_passes`: Validates AST validation accepts legitimate SELECT queries.
* `test_mutating_statements_rejected`: Verifies AST validation rejects DROP, DELETE, UPDATE, INSERT, ALTER.
* `test_multiple_statements_rejected`: Verifies semicolon-delimited SQL injection rejection.
* `test_nonexistent_table_rejected`: Verifies rejection of hallucinated tables outside the schema.
* `test_pipeline_end_to_end_exact_query`: Full pipeline execution on direct question.
* `test_pipeline_end_to_end_aggregation`: Full pipeline execution with multi-table joins and aggregation.
* `test_pipeline_clarification_on_ambiguity`: Full pipeline handling of ambiguous and unsupported queries.

---

## 6. Running the Benchmark Evaluation

Run the automated evaluation benchmark comparing the Datrics Text2SQL pipeline against the baseline:
```powershell
python -m app.evaluation.runner
```
Outputs execution accuracy, exact-match rates, table precision/recall, and latency to console and writes detailed records to `data/evaluation_results.json`.

---

## 7. Launching User Interfaces

### Streamlit Interactive Web App
```powershell
streamlit run app/ui/streamlit_app.py
```
Open your browser to `http://localhost:8501`. Features:
* Natural language question submission.
* Visual execution plan inspector (normalized question, progressive retrieval stage, selected tables, applied business rules).
* Formatted SQL syntax output with execution preview.
* Interactive database schema browser and example library explorer.

### FastAPI REST Endpoints
```powershell
uvicorn app.api.main:app --reload --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.
