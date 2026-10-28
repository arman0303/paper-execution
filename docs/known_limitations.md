# Known Limitations & Differences from Base Paper

This document explicitly details all engineering decisions, architectural differences, and experimental scope limitations between this reproduction and the original research paper **“Datrics Text2SQL: A Framework for Natural Language to SQL Query Generation”** (arXiv:2506.12234v1).

---

## 1. Paper-Reported Techniques vs. Implementation Scope

| Component | Paper Specification | Repository Implementation | Distinction & Rationale |
|---|---|---|---|
| **Benchmark Dataset** | Paper describes internal enterprise data and Spider/BIRD principles without publishing their internal dataset. | Curated realistic e-commerce schema with 22 train examples and 10 held-out test cases. | **Engineering Addition**: Required for local, open-source reproducibility. |
| **Progressive Retrieval Thresholds** | Paper names stages ($P_{95}, P_{99}, P_{01}$) and shows cumulative distribution curves without publishing explicit scalar cutoffs. | Configurable scalar cutoffs: $P_{95}=0.92$, $P_{99}=0.88$, $P_{01}=0.75$, exact match $=0.98$. | **Engineering Decision**: Empirical thresholds calibrated to SentenceTransformers embedding distances. |
| **Cross-Encoder Model** | Paper references Quora Duplicate Questions cross-encoder. | Implemented with `cross-encoder/ms-marco-MiniLM-L-6-v2` adapter (disabled by default). | **Engineering Decision**: MS-MARCO provides general passage-to-query ranking suitable for Text-to-SQL. |
| **Mock LLM Provider** | Not part of paper (paper tested commercial foundation models). | Offline `MockLLMProvider` with deterministic pattern synthesis. | **Engineering Addition**: Enables 100% offline, zero-cost unit testing and CI execution. |
| **AST Parser** | Mentions SQL validation and syntax checking. | Implemented with `sqlglot` AST traversal enforcing read-only SELECT and identifier whitelist. | **Engineering Addition**: Enforces formal security boundary. |
| **Read-Only Database Connection** | Discusses safe execution. | SQLite URI `mode=ro` and `PRAGMA query_only = ON`. | **Engineering Improvement**: Defense-in-depth against prompt injection. |

---

## 2. Experimental Limitations

1. **Small Curated Evaluation Set**:
   * The evaluation uses 10 held-out test cases. While sufficient to verify all pipeline branches (filtering, joins, aggregation, ambiguity detection, error repair), this is a prototype validation suite rather than an exhaustive benchmark like Spider (10,000+ examples) or BIRD.
2. **Offline Mock LLM vs. Live Foundation Models**:
   * Unit tests run by default with `LLM_PROVIDER=mock`. When switching to `gemini` or `openai`, generation quality depends on the external model's instruction following and zero-shot reasoning capabilities.
3. **ChromaDB File-Locking on Cloud Sync Drives**:
   * When running inside OneDrive, Google Drive, or Dropbox synced directories on Windows, ChromaDB's SQLite database lock may experience intermittent file contention. Setting `EMBEDDING_PROVIDER=tfidf` activates an in-memory cosine fallback that bypasses disk locks during testing.
