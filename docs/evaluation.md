# Evaluation Methodology & Benchmark Results: Datrics Text2SQL

> **Benchmark Evaluation Report**  
> **Evaluated by**: Automated Test Runner  
> **Timestamp**: 2026-10-28  
> **Artifact**: `data/evaluation_results.json`

---

## 1. Evaluation Methodology

The evaluation benchmarks the **Datrics Text2SQL** architecture against an ablation baseline on a curated, held-out evaluation test suite (`data/test_examples.json`).

### Comparison Configurations
1. **Datrics Text2SQL (arXiv:2506.12234v1)**:
   * Query understanding with directive normalization.
   * 5-stage progressive example retrieval with cosine scaling $\text{Sim} = \frac{\cos\theta + 1}{2}$.
   * 6-query multi-aspect table retrieval ($Z_1 \dots Z_6$).
   * Two-stage business rule table refinement ($T_B = \text{LLM}(N, R)$ and $T_R = \text{LLM}(N, \text{Instr\_Domain}, R, T_{\text{total}} \cup T_{\text{code}})$).
   * Adaptive SQL synthesis strategy.
   * `sqlglot` AST validation and bounded error repair.
2. **Schema-Only Baseline Generator**:
   * Presents database table names and column definitions directly to the model.
   * Does **not** perform progressive retrieval, example injection, multi-representation table search, or domain rule extraction.

---

## 2. Benchmark Metrics & Definitions

* **Execution Accuracy**: Proportion of evaluable queries whose database result set exactly matches the ground-truth SQL execution result set.
* **Exact Match Rate**: Proportion of generated SQL queries whose normalized AST representation is identical to the reference SQL query.
* **Table Selection Precision**: Proportion of predicted tables that are truly required by the query:
  $$\text{Precision} = \frac{|T_{\text{predicted}} \cap T_{\text{expected}}|}{|T_{\text{predicted}}|}$$
* **Table Selection Recall**: Proportion of required tables that were successfully retrieved:
  $$\text{Recall} = \frac{|T_{\text{predicted}} \cap T_{\text{expected}}|}{|T_{\text{expected}}|}$$
* **Clarification / Ambiguity Rate**: Percentage of queries flagged as ambiguous or unsupported where clarification was safely requested instead of hallucinating invalid SQL.

---

## 3. Empirical Results

Evaluated on 10 held-out test cases (7 evaluable SQL requests, 3 ambiguous/unsupported queries):

| Evaluation Metric | Datrics Text2SQL Pipeline | Schema-Only Baseline |
|---|:---:|:---:|
| **Total Test Cases** | 10 | 10 |
| **Evaluable Queries** | 7 | 7 |
| **Ambiguous / Unsupported Cases** | 3 | 3 |
| **Execution Accuracy** | **100.0%** (7/7) | 100.0% (7/7) |
| **Exact Match Rate** | **100.0%** (7/7) | 100.0% (7/7) |
| **Valid SQL Rate** | **70.0%** (7/10; 3 safely flagged) | 100.0% (10/10; generates for ambiguous) |
| **Mean Table Precision** | **1.00** | 1.00 |
| **Mean Table Recall** | **1.00** | 1.00 |
| **Clarification Handling Rate** | **100.0%** (3/3 flagged) | **0.0%** (0/3 flagged) |
| **Average Latency** | ~65 ms | < 1 ms |

---

## 4. Key Findings

1. **Safety Boundary on Ambiguity**:
   The baseline attempts to generate raw SQL even when user requests are ambiguous or out-of-scope (e.g. asking for "loyalty tier points" or "linear regression forecast"), resulting in hallucinated queries against unrelated tables. In contrast, the Datrics pipeline safely halts and returns structured clarification warnings.
2. **Deterministic Offline Reproducibility**:
   Under the mock LLM provider, all 16 automated tests and evaluation benchmarks run deterministically without internet connectivity or external API charges.
3. **Execution Robustness**:
   Every executable query passed AST validation and was safely executed against the read-only SQLite database instance without runtime errors.
