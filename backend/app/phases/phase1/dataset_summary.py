from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .column_classifier import classify_dataframe


# For very large datasets, expensive semantic-only operations are sampled.
# Core counts (rows, columns, missing, unique, duplicates) remain exact.
LARGE_DATASET_ROWS = 1_000_000
SEMANTIC_SAMPLE_ROWS = 200_000
SAMPLE_HEAD_ROWS = 2_000


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def _sample_values(series: pd.Series, limit: int = 12) -> list[Any]:
    """Get representative values without dropna() over a 10M-row column."""
    try:
        if len(series) <= SAMPLE_HEAD_ROWS:
            candidates = series
        else:
            candidates = pd.concat(
                [series.head(SAMPLE_HEAD_ROWS), series.tail(100)],
                ignore_index=True,
            )

        values = candidates.dropna().head(limit).tolist()
        return [_json_value(value) for value in values]
    except Exception:
        return []


def _numeric_profile(series: pd.Series) -> dict[str, Any]:
    """Fast numeric profile using the existing numeric dtype where possible."""
    try:
        numeric = series if pd.api.types.is_numeric_dtype(series) else pd.to_numeric(
            series, errors="coerce"
        )
        numeric = numeric.dropna()
        if numeric.empty:
            return {}

        return {
            "min": _json_value(numeric.min()),
            "max": _json_value(numeric.max()),
            "mean": _json_value(numeric.mean()),
            "median": _json_value(numeric.median()),
            "std": (
                _json_value(numeric.std(ddof=1))
                if len(numeric) > 1
                else 0.0
            ),
        }
    except Exception:
        return {}


def _top_values(series: pd.Series, limit: int = 8) -> list[dict[str, Any]]:
    """Top values are semantic evidence, not a UI-critical exact statistic."""
    try:
        source = series
        if len(series) > LARGE_DATASET_ROWS:
            # Keep semantic profiling bounded for 10M+ row datasets.
            source = pd.concat(
                [series.head(SEMANTIC_SAMPLE_ROWS)],
                ignore_index=True,
            )

        return [
            {"value": _json_value(key), "count": int(count)}
            for key, count in source.value_counts(dropna=True).head(limit).items()
        ]
    except Exception:
        return []


def _numeric_correlations(
    df: pd.DataFrame,
    *,
    max_relationships: int = 30,
) -> list[dict[str, Any]]:
    """Compute semantic correlations once, using a bounded sample for huge data."""
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return []

    try:
        if len(numeric) > LARGE_DATASET_ROWS:
            numeric = numeric.head(SEMANTIC_SAMPLE_ROWS)

        corr = numeric.corr(numeric_only=True)
        records: list[dict[str, Any]] = []

        columns = list(corr.columns)
        for i, first in enumerate(columns):
            for second in columns[i + 1:]:
                value = corr.loc[first, second]
                if pd.notna(value):
                    records.append({
                        "column_1": str(first),
                        "column_2": str(second),
                        "correlation": round(float(value), 4),
                    })

        records.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        return records[:max_relationships]
    except Exception:
        return []


def build_summary(
    df: pd.DataFrame,
    filename: str,
    file_size: int,
) -> dict[str, Any]:
    """
    Build the Phase 1 summary without repeatedly rescanning a huge dataframe.

    Exact:
      - row/column counts
      - missing counts
      - unique counts
      - duplicate row count
      - classification

    Sampled only where the value is semantic evidence for the LLM:
      - top values on >1M rows
      - numeric relationships on >1M rows
      - representative values
    """
    profiles = classify_dataframe(df)

    groups = {
        "numeric": [c for c, p in profiles.items() if p["kind"] == "numeric"],
        "categorical": [c for c, p in profiles.items() if p["kind"] == "categorical"],
        "datetime": [c for c, p in profiles.items() if p["kind"] == "datetime"],
        "identifiers": [c for c, p in profiles.items() if p["kind"] == "identifier"],
        "boolean": [c for c, p in profiles.items() if p["kind"] == "boolean"],
        "null_empty": [c for c, p in profiles.items() if p["kind"] == "null_empty"],
    }

    # One dataframe-wide missing aggregation instead of df.isna() per column.
    total_missing = int(sum(p["missing_values"] for p in profiles.values()))

    # Exact duplicate detection is intentionally preserved because Phase 1
    # exposes this metric to later phases.
    duplicate_records = int(df.duplicated(keep="first").sum())

    columns_with_missing = [
        column for column, profile in profiles.items()
        if profile["missing_values"] > 0
    ]

    column_details: dict[str, Any] = {}
    for column, raw_profile in profiles.items():
        profile = dict(raw_profile)
        series = df[column]

        profile["sample_values"] = _sample_values(series)

        profile["top_values"] = _top_values(series)

        if profile["kind"] == "numeric":
            profile["numeric_profile"] = _numeric_profile(series)

        column_details[column] = profile

    summary = {
        "dataset_id": None,
        "filename": filename,
        "file_size_bytes": int(file_size),
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "numeric": len(groups["numeric"]),
        "categorical": len(groups["categorical"]),
        "datetime": len(groups["datetime"]),
        "identifiers": len(groups["identifiers"]),
        "boolean": len(groups["boolean"]),
        "null_empty": len(groups["null_empty"]),
        "total_missing_values": total_missing,
        "duplicate_records": duplicate_records,
        "columns_with_missing": len(columns_with_missing),
        "numeric_column_names": groups["numeric"],
        "categorical_column_names": groups["categorical"],
        "datetime_column_names": groups["datetime"],
        "identifier_column_names": groups["identifiers"],
        "boolean_column_names": groups["boolean"],
        "null_column_names": groups["null_empty"],
        "columns_with_missing_names": columns_with_missing,
        "all_column_names": [str(column) for column in df.columns],
        "column_details": column_details,
        "column_profiles": column_details,
        # Additive field used by the optimized LLM context builder.
        "numeric_relationships": _numeric_correlations(df),
    }

    return summary
