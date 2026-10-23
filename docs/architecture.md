# Datrics Text2SQL Architecture & Design

This document details the architecture of the Datrics Text2SQL framework, reproducing and extending the methodology described in **arXiv:2506.12234v1**.

```
+----------------------------------------------------------------------------------------------------+
|                                    DATRICS TEXT2SQL ARCHITECTURE                                   |
+----------------------------------------------------------------------------------------------------+

[ Knowledge Base Ingestion & Training ]
 1. SQLite Database Schema ---> Introspection ---> Schema Metadata (tables, columns, types, FKs)
 2. Unstructured/Semi-structured Docs ---> LLM Processing ---> Structured Table Documentation (JSON)
      |
      +---> Repeated Concept Extraction (i=1..N runs) ---> Frequency Voting ---> Strong Entities
      |
 3. Question-SQL Examples (Ak) ---> LLM Normalization:
      |--> Normalized Question (Nk)
      |--> Main Clause (Mk) & Details (M'k)
      |--> Extracted Entities (Ek) [Minor Em vs Major EM]
      |--> Data Sources (Vk: tables & columns)
      |--> Operations (Ok: aggregations, filters, groupings)
      |--> Paraphrase Generation (3 question variations)
 4. Multi-Representation ChromaDB Indexing:
      |--> Table Docs Collection: 5 views (description, connected_tables, table_name, entity, full doc)
      |--> Q-SQL Examples Collection: 7 vectors per example (Init, 3x Variations, Normalized, Main, Entities)
 5. Domain Rules & Entity-to-Table Mappings (Instr_Domain = f_text(U E'k))

------------------------------------------------------------------------------------------------------

[ Query Processing & Retrieval Pipeline ]
 Incoming User Question (I)
         |
         v
 [ Query Understanding (LLM) ] ---> Structured Representation:
                                       Nk (Normalized), Mk (Main Clause), Ek (Entities),
                                       Operations, Potential Filters/Dimensions
         |
         +-------------------------------------------------------------------+
         |                                                                   |
         v                                                                   v
 [ Progressive Example Retrieval ]                                  [ Table Retrieval ]
 Stage 1: Exact Match (Sim -> 1)                                    6 Multi-Representation
          |-- Matched? -> Return Stored SQL directly!                Vector Queries (Z1..Z6):
          |                                                          - Z1: M in (desc, entity)
 Stage 2: Normalized Match (Sim >= P95)                              - Z2: N in (desc, entity)
          |-- Matched? -> S_code** (Exact Example)                   - Z3: E in (conn_tables, entity)
          |                                                          - Z4: M in (table_name)
 Stage 3: Main Clause Match (Sim >= P99)                             - Z5: N in (table_name)
          |-- Matched? -> S_code* (Strongly Aligned Example)         - Z6: E in (table_name)
          |                                                                   |
 Stage 4: Expanded Search (Sim >= P01)                                        v
          |-- Collect candidates A'_res                             Union & Deduplicate -> T_det
          |                                                                   |
 Stage 5: Optional Cross-Encoder Reranker                                     v
          |-- Passed tau'? -> S_code*                               [ Business Rules Table Search ]
          |-- Else: S_code (Template Reference)                     TB = LLM(N, R)
                                                                              |
                                                                              v
                                                                    T_total = T_det U TB
         +--------------------------------------------------------------------+
         |
         v
 [ LLM-Driven Table Refinement ]
 Input: N, Instr_Domain, Business Rules R, Candidate Tables (T_total U T_code)
 Reasoning: Table coverage analysis, join path completeness, schema constraints
 Output: Refined table set T_R with justifications

------------------------------------------------------------------------------------------------------

[ SQL Generation, Validation & Execution ]
 Input: Normalized Query (N), Schema / Descriptions (T_R / T_code), Examples (S)
 Strategy Selection:
   - Direct Output (S_sql^R)
   - Exact Example-Driven (S_code**)
   - Strongly Aligned Example-Driven (S_code*)
   - Flexible Template / Documentation-Driven (S_code + T_R)
         |
         v
 [ SQL Synthesizer (LLM) ] ---> Candidate SQL Query
         |
         v
 [ SQL Security & AST Validation (sqlglot) ]
   - Validate only single-statement SELECT / safe CTEs
   - Prohibit INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, ATTACH
   - Validate table and column names exist in actual schema
         |
         +--> Validation Failure? ---> Bounded Self-Correction Loop (max 2 attempts)
         |
         v
 [ Safe Read-Only Execution ]
   - SQLite read-only mode (mode=ro, PRAGMA query_only=ON)
   - Query execution timeout (5s) & max row limit (100)
         |
         v
 [ UI Display & Evaluation Diagnostics ]
   - Generated SQL, Execution Results Table, Strategy Used,
     Retrieved Examples with Similarity Scores, Refined Tables with Reasoning
```
