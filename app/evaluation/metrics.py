from typing import List, Set, Dict, Any
import sqlglot

def normalize_sql(sql_str: str) -> str:
    """Normalizes SQL formatting for exact match comparison."""
    try:
        parsed = sqlglot.parse_one(sql_str, read="sqlite")
        return parsed.sql(dialect="sqlite", pretty=False).strip().lower()
    except Exception:
        return " ".join(sql_str.strip().lower().split()).rstrip(";")

def compute_table_precision_recall(predicted_tables: List[str], expected_tables: List[str]) -> Dict[str, float]:
    pred_set = set(t.lower() for t in predicted_tables)
    exp_set = set(t.lower() for t in expected_tables)

    if not exp_set:
        return {"precision": 1.0 if not pred_set else 0.0, "recall": 1.0}

    intersection = pred_set.intersection(exp_set)
    precision = len(intersection) / len(pred_set) if pred_set else 0.0
    recall = len(intersection) / len(exp_set) if exp_set else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4)
    }

def are_results_equal(rows_a: List[List[Any]], rows_b: List[List[Any]]) -> bool:
    """
    Compares query execution result sets for execution accuracy,
    handling row ordering differences when queries don't specify strict order.
    """
    if len(rows_a) != len(rows_b):
        return False

    # Try set comparison of stringified rows
    try:
        set_a = sorted([str(r) for r in rows_a])
        set_b = sorted([str(r) for r in rows_b])
        return set_a == set_b
    except Exception:
        return rows_a == rows_b
