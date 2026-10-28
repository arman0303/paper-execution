# Implementation Audit: Datrics Text2SQL (arXiv:2506.12234v1)

> **Audited by**: AI/ML Engineering Review  
> **Date**: 2026-10-28  
> **Repository**: https://github.com/arman0303/paper-execution  
> **Paper**: *Datrics Text2SQL: A Framework for Natural Language to SQL Query Generation* (Gladkykh & Kirykov, Datrics, 2025)

---

## 1. Requirements Traceability Matrix

| # | Paper Component | Paper Section | Impl Files | Status | Gaps Found | Priority |
|---|---|---|---|---|---|---|
| A | Database Schema Ingestion & Documentation Generation | §II.A, p.3–7 | `app/database/introspection.py`, `app/ingestion/doc_generator.py` | **Partially Implemented** | `TableDocGenerator` exists but is **never called** from the main pipeline. `IndexingPipeline` skips generation and reads from the static `data/table_docs.json` file directly. Automatic schema-refresh is not wired in. | HIGH |
| B | Frequency-Based Entity Voting (`strong_entities`) | §II.A p.5–6 | `app/ingestion/entity_voting.py` | **Implemented** | Logic correct. Called by `TableDocGenerator` which is itself bypassed. Entity voting results only reach the system if `table_docs.json` is pre-populated. | MEDIUM |
| C | Query Understanding: Nk, Mk, M'k, Ek | §II.C p.8–10 | `app/query_understanding/analyzer.py` | **Implemented** | All five fields extracted. Mock LLM responses are deterministic. Regex fallback is safe. **Minor gap**: `normalize_question` prompt does not include the full multi-step normalization rule from paper p.9 (step 3: "replace entity values with placeholders"). | LOW |
| D | Multi-Vector Q-SQL Example Cloud Ak=(Ik, Scode_k, Nk, Mk, M'k, Ek, Vk, Ok) | §II.B p.10–12 | `app/schemas/example.py`, `app/knowledge_base/indexing_pipeline.py` | **Partially Implemented** | 7 representations stored (initial, norm, main, entities, 3 variations). **Gap**: The paper's `Ok` (operation representation) and `M'k` (details) are stored as fields in `NormalizedExample` but are **not embedded as separate vector entries**. Only 5–7 representations are indexed depending on entity presence. | MEDIUM |
| E | Progressive Example Retrieval (5 stages) | §II.D p.16–21 | `app/retrieval/progressive_example.py` | **Implemented** | All 5 stages present with correct paper formula `Sim=(cos+1)/2`. **Gaps**: (1) Stage 4 uses `norm_q` but paper specifies the expanded query includes the raw question too; (2) threshold names match paper terminology but paper does not publish exact numeric values — current values are engineering estimates (documented in config); (3) duplicate deduplication only checks `example_id`, not `sql` content. | LOW |
| F | Multi-Representation Table Retrieval (Z1–Z6) | §II.E p.22–23 | `app/retrieval/table_retrieval.py` | **Implemented** | All 6 queries present. **Gap**: Z1–Z3 query descriptions in code match paper. However the paper specifies Z1–Z2 target `[description, entity]` and Z3 targets `[connected_tables, entity]` — this is correctly reproduced. Z4–Z6 use `[table_name]` category — also correct. No significant gap. | NONE |
| G | Business Rule Extraction & Two-Stage Table Refinement | §II.F p.24–25 | `app/table_refinement/refiner.py`, `data/business_rules.json` | **Implemented** | TB = LLM(N, R) and TR = LLM(N, Instr_Domain, R, T_total ∪ T_code) both implemented. **Gap**: Mock LLM trigger detection in `mock_provider.py` for table refinement checks for `"refine table selection based on business rules"` but the actual prompt text is `"Given the normalized user question and domain business rules"` — **mock never fires Stage 1 correctly**. | HIGH |
| H | Instr_Domain (Minor/Major Entity Classification) | §II.C p.12–14 | `app/knowledge_base/domain_rules.py` | **Partially Implemented** | Em/EM extracted from training examples. `instructions_text` is hardcoded with e-commerce domain mappings rather than derived dynamically from examples. | LOW |
| I | Adaptive SQL Generation (4 strategies) | §II.G p.25–27 | `app/sql_generation/generator.py`, `app/sql_generation/strategies.py` | **Implemented** | All 4 strategies present. Strategy selection logic maps stages correctly. **Minor gap**: EXACT_EXAMPLE and STRONGLY_ALIGNED strategies both use the same prompt structure — paper suggests STRONGLY_ALIGNED should emphasize schema adaptation over direct SQL reuse. | LOW |
| J | AST SQL Validation (read-only boundary) | §II.H p.28 | `app/sql_validation/validator.py` | **Implemented** | `sqlglot` AST parsing, SELECT-only enforcement, multi-statement rejection, identifier validation all working. | NONE |
| K | Safe SQL Execution with timeout & row limit | §II.H p.28 | `app/sql_validation/executor.py` | **Implemented** | Read-only URI connection, busy timeout, row limit applied. **Minor gap**: Timeout enforcement uses `busy_timeout` (lock wait), not a true query execution timeout. For SQLite this is acceptable; documented below. | LOW |
| L | Bounded Error Correction Loop | §II.H p.28 | `app/pipeline.py` lines 122–156 | **Implemented** | Retry loop with `MAX_SQL_CORRECTION_ATTEMPTS=2` is correct. Error fed back into generation prompt. Revalidation happens before re-execution. | NONE |
| M | Cosine Similarity Formula Sim=(cosθ+1)/2 | Paper p.16 | `app/embeddings/sentence_transformer.py` | **Implemented** | Formula correctly applied in both Chroma distance conversion and in-memory fallback. | NONE |
| N | ChromaDB Multi-Collection Vector Store | §II.B | `app/knowledge_base/vector_store.py` | **Implemented** | Two collections (`table_docs`, `query_examples`). Category/representation metadata filters working. In-memory fallback for offline tests. **Gap**: ChromaDB `where` filter with single item uses dict not list — this is the correct Chroma API usage, but `$in` operator for lists may fail on older Chroma versions. | LOW |
| O | Cross-Encoder Reranker (Stage 5) | §II.D p.20 | `app/retrieval/reranker.py` | **Implemented (disabled by default)** | ENABLE_RERANKER=False default. Cross-encoder loads `cross-encoder/ms-marco-MiniLM-L-6-v2`. Paper mentions Quora duplicate detection — the ms-marco model is appropriate for passage reranking but not specifically Quora duplicate detection. Documented as engineering decision. | LOW |
| P | Evaluation: Execution Accuracy, Exact Match | §III | `app/evaluation/runner.py`, `app/evaluation/metrics.py` | **Implemented** | Metrics computed correctly. **Critical gap**: README claims "100% Execution Accuracy (7/7 evaluable)" — this is produced entirely by the MockLLM which returns hardcoded SQL matching the expected outputs. This is **not a valid evaluation**. Results are mock-generated, not real LLM performance. | CRITICAL |
| Q | Baseline (Schema-Only) Comparison | §III | `app/evaluation/baseline.py` | **Implemented** | Correct schema-only generator. Same MockLLM issue applies — baseline also returns hardcoded SQL matching expected queries. | CRITICAL |
| R | Table Documentation Schema (full JSON) | §II.A p.3 | `app/schemas/documentation.py`, `data/table_docs.json` | **Implemented** | Schema matches paper exactly: name, summary, purpose, dependencies_thoughts, keys, connected_tables, columns, entities, strong_entities. | NONE |
| S | `data/payments` table — column `status` missing from schema | data layer | `data/table_docs.json` line 88 | **BUG** | `table_docs.json` has a malformed JSON record in the `payments` table: `"payment_method"` field includes a nested `"status"` key instead of a separate column object. The `status` column is missing from the columns array, breaking column-level documentation for `payments`. | HIGH |

---

## 2. Ordered Gap List (by priority)

### CRITICAL
1. **Mock evaluation inflates metrics to 100%**: The benchmark results reported in README (100% execution accuracy, 100% exact match) are produced entirely by a MockLLM with hardcoded pattern-matched responses. With a real LLM, results will differ. The evaluation framework is correct but the reported numbers are not meaningful for general LLM performance.

### HIGH
2. **`TableDocGenerator` bypassed**: Pipeline reads `data/table_docs.json` statically. Automatic schema-refresh and dynamic documentation generation (including entity voting) are not integrated into the pipeline startup.
3. **Mock LLM table refinement bug**: `mock_provider.py` trigger for Stage 1 business-rule refinement (`"refine table selection based on business rules"`) does not match the actual prompt string (`"Given the normalized user question and domain business rules"`), causing the MockLLM to fall through to a generic JSON response instead of returning the expected table list.
4. **`payments.status` column missing** from `data/table_docs.json` due to malformed JSON structure.

### MEDIUM
5. **`Ok` (operation) and `M'k` (details) representations not embedded**: The paper's example cloud `Ak` includes operation and details representations as separate embeddings. Current implementation stores these as object fields but does not create separate vector entries for them.
6. **Evaluation with real LLM not validated**: Tests pass with mock; no test coverage for real LLM providers with actual API calls.

### LOW
7. Stage 4 expanded query does not include raw question (only normalized).
8. STRONGLY_ALIGNED prompt identical to EXACT_EXAMPLE prompt — should differ.
9. `domain_rules.py` instruction text is mostly hardcoded rather than dynamically derived.
10. `busy_timeout` used instead of true query execution timeout.
11. No `docs/implementation_audit.md`, `docs/paper_to_code_mapping.md`, `docs/setup_and_execution.md`, `docs/evaluation.md`, `docs/known_limitations.md` existed before this audit.
12. Cross-encoder uses ms-marco rather than Quora duplicate detection model.
13. No test for missing retrieval examples, empty index, injection attempts through question text.
14. ChromaDB `$in` filter compatibility not tested across versions.

---

## 3. Component Classification Summary

| Status | Components |
|---|---|
| ✅ Implemented | C, F, I, J, K, L, M, N, O, R |
| ⚠️ Partially Implemented | A, B, D, H |
| 🐛 Has Bug | G (mock trigger mismatch), S (payments schema) |
| ❌ Not Verifiable without Real LLM | P, Q (evaluation numbers) |

---

## 4. Bugs Identified

### BUG-001: Mock LLM table refinement trigger mismatch
- **File**: `app/llm/mock_provider.py` line 109
- **Symptom**: Stage 1 business-rule table extraction (`refine_with_business_rules`) sends prompt `"Given the normalized user question and domain business rules..."` but MockLLM checks for `"refine table selection based on business rules"` — strings never match. MockLLM falls through to generic `{"status": "ok"}` response. `TableRefiner.refine_with_business_rules()` returns `[]` for all questions when using MockLLM.
- **Fix**: Add matching trigger strings to MockLLM.

### BUG-002: Malformed `payments` column in `table_docs.json`
- **File**: `data/table_docs.json` lines 87–89
- **Symptom**: `payments.payment_method` column object contains a nested `"status"` key instead of being a separate column entry. The `payments.status` column (outcome: successful/failed/refunded) is completely absent from documentation, meaning retrieval will never match payment-status-related questions to the `payments` table via entity search.
- **Fix**: Correct the JSON structure.

### BUG-003: `IndexingPipeline` never calls `TableDocGenerator`
- **File**: `app/knowledge_base/indexing_pipeline.py` line 36–41
- **Symptom**: `load_data_files()` reads from static `data/table_docs.json`. If this file is absent or stale, the pipeline silently loads empty docs. Schema changes in the database are never reflected without manually regenerating the JSON.
- **Fix**: Add optional `generate_docs_if_missing` mode to `IndexingPipeline`.

---

## 5. Files to be Created/Modified

| Action | File | Reason |
|---|---|---|
| FIX | `app/llm/mock_provider.py` | Bug-001: add missing trigger string for table refinement stage 1 |
| FIX | `data/table_docs.json` | Bug-002: fix payments.status column |
| ADD | `app/ingestion/generate_docs.py` | CLI script to run `TableDocGenerator` and save `table_docs.json` |
| MODIFY | `app/knowledge_base/indexing_pipeline.py` | Optional doc-generation integration |
| ADD | `app/retrieval/reranker.py` | Already exists — add model name documentation comment |
| ADD | `tests/test_ingestion.py` | Tests for entity voting, doc generation, example enricher |
| ADD | `tests/test_table_refinement.py` | Tests for TB and TR stages with mock |
| ADD | `tests/test_pipeline_integration.py` | Integration test for full pipeline with SQLite |
| ADD | `docs/implementation_audit.md` | This file |
| ADD | `docs/paper_to_code_mapping.md` | Detailed section-by-section mapping |
| ADD | `docs/setup_and_execution.md` | Complete setup guide |
| ADD | `docs/evaluation.md` | Evaluation methodology, results, and limitations |
| ADD | `docs/known_limitations.md` | Honest enumeration of gaps |
| ADD | `.env.example` | Already exists — verify completeness |
