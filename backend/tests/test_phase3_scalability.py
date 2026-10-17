import numpy as np
import pandas as pd

from app.phases.phase3.preprocessing import (
    INSPECTION_DETAIL_LIMIT,
    build_preprocessing_inspection,
    preprocess_dataset,
)
from app.phases.phase3.statistical_analysis import analyze_statistics


def test_large_inspection_keeps_exact_counts_but_bounds_details():
    n = 12_000
    df = pd.DataFrame({
        "category": ["same"] * n,
        "value": np.arange(n, dtype=float),
        "missing": [None] * 150 + list(range(n - 150)),
    })
    summary = {
        "numeric_column_names": ["value", "missing"],
        "categorical_column_names": ["category"],
        "datetime_column_names": [],
        "identifier_column_names": ["value"],
        "boolean_column_names": [],
    }

    result = build_preprocessing_inspection(df, list(df.columns), summary)
    by_name = {item["column"]: item for item in result["columns"]}

    assert result["row_count"] == n
    assert result["missingTotal"] == 150
    assert by_name["category"]["duplicate_values"] == n
    assert by_name["category"]["duplicate_records_truncated"] is True
    assert sum(len(group["records"]) for group in by_name["category"]["duplicate_records"]) <= INSPECTION_DETAIL_LIMIT
    assert len(by_name["missing"]["missing_records"]) == INSPECTION_DETAIL_LIMIT
    assert by_name["missing"]["missing_records_truncated"] is True


def test_large_preprocessing_response_is_bounded_and_data_is_preserved():
    n = 12_000
    df = pd.DataFrame({
        "id": np.arange(n),
        "value": np.arange(n, dtype=float),
        "category": ["A", "B"] * (n // 2),
    })
    summary = {
        "numeric_column_names": ["id", "value"],
        "categorical_column_names": ["category"],
        "datetime_column_names": [],
        "identifier_column_names": ["id"],
        "boolean_column_names": [],
    }
    processed, result = preprocess_dataset(df, list(df.columns), summary)

    assert len(processed) == n
    assert len(result["rows"]) == 100
    assert result["rows_truncated"] is True
    assert result["duplicate_records_removed"] == 0


def test_expensive_statistics_use_bounded_samples():
    n = 3_000
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="h"),
        "x": rng.normal(size=n),
        "y": rng.normal(size=n),
        "group": rng.choice(["a", "b", "c"], size=n),
    })
    summary = {
        "numeric_column_names": ["x", "y"],
        "categorical_column_names": ["group"],
        "datetime_column_names": ["date"],
        "identifier_column_names": [],
        "boolean_column_names": [],
    }

    result = analyze_statistics(df, list(df.columns), summary)
    assert result["analysis_completed"] is True
    assert result["sections"]["cluster"]["cluster_analysis"]["sampled"] is True
    assert result["sections"]["density"]["density_analysis"]["sampled"] is True
