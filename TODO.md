# Datrics Text2SQL Project Roadmap & Task Tracker

- [x] **Phase 1: Foundation & Planning**
  - [x] Analyze research paper (arXiv:2506.12234v1)
  - [x] Create Implementation Plan & Paper-to-Code mapping
  - [x] Initialize project directory structure and environment files (`.gitignore`, `.env.example`, `requirements.txt`)
  - [x] Install / verify required dependencies
  - [x] Create realistic e-commerce SQLite database and seed data (`data/sample_ecommerce.db`)
  - [x] Create curated question-SQL training and test datasets

- [x] **Phase 2: Core Engine (Minimum Working System)**
  - [x] Pydantic Schemas (`documentation`, `example`, `query_understanding`, `retrieval`, `sql`)
  - [x] Configuration manager (`app/config.py`)
  - [x] Database introspection & read-only connection manager (`app/database/`)
  - [x] Provider-independent LLM adapter (`Gemini`, `OpenAI`, `MockLLM`)
  - [x] Embedding adapter with local fallback (`app/embeddings/`)
  - [x] Knowledge base storage with ChromaDB (`app/knowledge_base/vector_store.py`)
  - [x] Query understanding analyzer (`app/query_understanding/analyzer.py`)
  - [x] Progressive example retrieval & candidate selection (`app/retrieval/`)
  - [x] Dynamic SQL generation strategies (`app/sql_generation/`)
  - [x] AST SQL validation & safe read-only executor (`app/sql_validation/`)
  - [x] End-to-end pipeline orchestrator (`app/pipeline.py`)
  - [x] Streamlit UI with query tester and schema inspector (`app/ui/streamlit_app.py`)

- [x] **Phase 3: Advanced Paper Components**
  - [x] Multi-run entity extraction with frequency voting (`app/ingestion/entity_voting.py`)
  - [x] Paraphrase question variation generator (7 embeddings per example)
  - [x] Domain-specific entity classification (Minor $E_m$, Major $E_M$) and rule derivation
  - [x] Multi-aspect table documentation retrieval ($Z_1..Z_6$ with metadata categories)
  - [x] Two-stage table refinement ($T_B = LLM(N, R)$, $T_R = LLM(N, Instr\_Domain, R, T_{total} \cup T_{code})$)
  - [x] Cross-encoder reranking integration

- [x] **Phase 4: Verification & Reproducible Evaluation**
  - [x] Comprehensive unit and integration test suite (`tests/` - 16 passing tests)
  - [x] Evaluation runner comparing Baseline (schema only) vs Datrics RAG pipeline
  - [x] Metrics reporting (Execution accuracy, valid SQL %, table selection precision/recall, latency)

- [x] **Phase 5: Documentation & Presentation**
  - [x] Architecture design document (`docs/architecture.md`)
  - [x] Paper mapping and implementation notes (`docs/paper_mapping.md`)
  - [x] Beginner-friendly README with Windows 11 / PowerShell setup guide
