import json
import time
from pathlib import Path
from typing import Dict, Any, List
from app.pipeline import DatricsText2SQLPipeline
from app.evaluation.baseline import SchemaOnlyBaselineGenerator
from app.evaluation.metrics import normalize_sql, compute_table_precision_recall, are_results_equal
from app.sql_validation.validator import SQLValidator
from app.sql_validation.executor import SafeSQLExecutor
from app.database.connection import DatabaseConnectionManager
from app.config import settings

def run_evaluation(output_file: str = "data/evaluation_results.json"):
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    test_file = data_dir / "test_examples.json"

    with open(test_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    # Initialize Systems
    pipeline = DatricsText2SQLPipeline()
    baseline = SchemaOnlyBaselineGenerator(table_docs=pipeline.indexing_pipeline.table_docs)
    validator = SQLValidator(allowed_tables=list(pipeline.indexing_pipeline.table_docs.keys()))
    conn_mgr = DatabaseConnectionManager(settings.DATABASE_PATH)
    executor = SafeSQLExecutor(conn_mgr)

    results = {
        "metadata": {
            "experiment": "Datrics Text2SQL vs Schema-Only Baseline",
            "paper_reference": "arXiv:2506.12234v1",
            "disclaimer": "Prototype empirical comparison on curated test suite. Not a reproduction of an unreported benchmark.",
            "test_cases_count": len(test_cases),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        "summary": {},
        "details": []
    }

    # Tracking counters
    datrics_exact_match = 0
    datrics_exec_acc = 0
    datrics_valid_sql = 0
    datrics_precisions = []
    datrics_recalls = []
    datrics_latencies = []
    datrics_clarifications = 0

    base_exact_match = 0
    base_exec_acc = 0
    base_valid_sql = 0
    base_precisions = []
    base_recalls = []
    base_latencies = []

    print(f"\n=======================================================")
    print(f"  RUNNING EVALUATION ON {len(test_cases)} HELD-OUT TEST CASES")
    print(f"=======================================================\n")

    for tc in test_cases:
        qid = tc["id"]
        question = tc["question"]
        expected_sql = tc.get("expected_sql")
        expected_tables = tc.get("expected_tables", [])
        is_ambiguous = tc.get("is_ambiguous", False)
        is_unsupported = tc.get("is_unsupported", False)

        # Ground truth execution
        expected_exec = None
        if expected_sql:
            expected_exec = executor.execute(expected_sql)

        # 1. Run Datrics Text2SQL Pipeline
        start_d = time.perf_counter()
        d_res = pipeline.process_query(question)
        latency_d = (time.perf_counter() - start_d) * 1000.0
        datrics_latencies.append(latency_d)

        d_valid = d_res.validation.is_valid if d_res.validation else False
        if d_valid:
            datrics_valid_sql += 1

        d_exact = False
        d_exec_acc = False
        if expected_sql and d_res.sql:
            d_exact = normalize_sql(d_res.sql) == normalize_sql(expected_sql)
            if d_res.execution and expected_exec and expected_exec.success:
                d_exec_acc = are_results_equal(d_res.execution.rows, expected_exec.rows)

        if d_exact:
            datrics_exact_match += 1
        if d_exec_acc:
            datrics_exec_acc += 1
        if d_res.clarification_requested:
            datrics_clarifications += 1

        d_pr = compute_table_precision_recall(d_res.referenced_tables, expected_tables)
        if expected_tables:
            datrics_precisions.append(d_pr["precision"])
            datrics_recalls.append(d_pr["recall"])

        # 2. Run Baseline
        start_b = time.perf_counter()
        b_res = baseline.generate(question)
        latency_b = (time.perf_counter() - start_b) * 1000.0
        base_latencies.append(latency_b)

        b_val = validator.validate(b_res.sql)
        b_valid = b_val.is_valid
        if b_valid:
            base_valid_sql += 1

        b_exec = executor.execute(b_res.sql) if b_valid else None
        b_exact = False
        b_exec_acc = False
        if expected_sql and b_res.sql:
            b_exact = normalize_sql(b_res.sql) == normalize_sql(expected_sql)
            if b_exec and expected_exec and expected_exec.success:
                b_exec_acc = are_results_equal(b_exec.rows, expected_exec.rows)

        if b_exact:
            base_exact_match += 1
        if b_exec_acc:
            base_exec_acc += 1

        b_pr = compute_table_precision_recall(b_res.referenced_tables, expected_tables)
        if expected_tables:
            base_precisions.append(b_pr["precision"])
            base_recalls.append(b_pr["recall"])

        case_record = {
            "id": qid,
            "question": question,
            "expected_sql": expected_sql,
            "datrics": {
                "generated_sql": d_res.sql,
                "strategy": d_res.strategy_used.value,
                "is_valid": d_valid,
                "exact_match": d_exact,
                "execution_accuracy": d_exec_acc,
                "clarification": d_res.clarification_requested,
                "table_metrics": d_pr,
                "latency_ms": round(latency_d, 2)
            },
            "baseline": {
                "generated_sql": b_res.sql,
                "is_valid": b_valid,
                "exact_match": b_exact,
                "execution_accuracy": b_exec_acc,
                "table_metrics": b_pr,
                "latency_ms": round(latency_b, 2)
            }
        }
        results["details"].append(case_record)
        print(f"[{qid}] Executed. Datrics Exact: {d_exact} | ExecAcc: {d_exec_acc} | Baseline ExecAcc: {b_exec_acc}")

    # Compute Summary
    n_total = len(test_cases)
    n_evaluable = len([tc for tc in test_cases if tc.get("expected_sql")])

    summary = {
        "datrics_text2sql": {
            "valid_sql_rate": round(datrics_valid_sql / n_total, 4),
            "exact_match_rate": round(datrics_exact_match / n_evaluable, 4) if n_evaluable else 0.0,
            "execution_accuracy": round(datrics_exec_acc / n_evaluable, 4) if n_evaluable else 0.0,
            "mean_table_precision": round(sum(datrics_precisions) / len(datrics_precisions), 4) if datrics_precisions else 0.0,
            "mean_table_recall": round(sum(datrics_recalls) / len(datrics_recalls), 4) if datrics_recalls else 0.0,
            "clarification_rate": round(datrics_clarifications / n_total, 4),
            "mean_latency_ms": round(sum(datrics_latencies) / len(datrics_latencies), 2)
        },
        "baseline_schema_only": {
            "valid_sql_rate": round(base_valid_sql / n_total, 4),
            "exact_match_rate": round(base_exact_match / n_evaluable, 4) if n_evaluable else 0.0,
            "execution_accuracy": round(base_exec_acc / n_evaluable, 4) if n_evaluable else 0.0,
            "mean_table_precision": round(sum(base_precisions) / len(base_precisions), 4) if base_precisions else 0.0,
            "mean_table_recall": round(sum(base_recalls) / len(base_recalls), 4) if base_recalls else 0.0,
            "clarification_rate": 0.0,
            "mean_latency_ms": round(sum(base_latencies) / len(base_latencies), 2)
        }
    }
    results["summary"] = summary

    # Save to file
    out_path = Path(__file__).resolve().parent.parent.parent / output_file
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n================== SUMMARY RESULTS ==================")
    print(f"Datrics Text2SQL:")
    print(f"  Valid SQL Rate:        {summary['datrics_text2sql']['valid_sql_rate'] * 100:.1f}%")
    print(f"  Execution Accuracy:    {summary['datrics_text2sql']['execution_accuracy'] * 100:.1f}%")
    print(f"  Exact Match Rate:      {summary['datrics_text2sql']['exact_match_rate'] * 100:.1f}%")
    print(f"  Table Precision:       {summary['datrics_text2sql']['mean_table_precision']:.2f}")
    print(f"  Table Recall:          {summary['datrics_text2sql']['mean_table_recall']:.2f}")
    print(f"  Clarification Rate:    {summary['datrics_text2sql']['clarification_rate'] * 100:.1f}%")
    print(f"\nBaseline (Schema Only):")
    print(f"  Valid SQL Rate:        {summary['baseline_schema_only']['valid_sql_rate'] * 100:.1f}%")
    print(f"  Execution Accuracy:    {summary['baseline_schema_only']['execution_accuracy'] * 100:.1f}%")
    print(f"  Exact Match Rate:      {summary['baseline_schema_only']['exact_match_rate'] * 100:.1f}%")
    print(f"=====================================================\n")
    print(f"Saved full results to {out_path}")
    return results

if __name__ == "__main__":
    run_evaluation()
