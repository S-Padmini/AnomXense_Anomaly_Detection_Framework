from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .column_classifier import classify_dataframe


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
    return [_json_value(v) for v in series.dropna().head(limit).tolist()]


def _numeric_profile(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {}
    return {
        "min": _json_value(numeric.min()),
        "max": _json_value(numeric.max()),
        "mean": _json_value(numeric.mean()),
        "median": _json_value(numeric.median()),
        "std": _json_value(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0,
    }


def build_summary(df: pd.DataFrame, filename: str, file_size: int) -> dict[str, Any]:
    profiles = classify_dataframe(df)

    groups = {
        "numeric": [c for c, p in profiles.items() if p["kind"] == "numeric"],
        "categorical": [c for c, p in profiles.items() if p["kind"] == "categorical"],
        "datetime": [c for c, p in profiles.items() if p["kind"] == "datetime"],
        "identifiers": [c for c, p in profiles.items() if p["kind"] == "identifier"],
        "boolean": [c for c, p in profiles.items() if p["kind"] == "boolean"],
        "null_empty": [c for c, p in profiles.items() if p["kind"] == "null_empty"],
    }

    column_details: dict[str, Any] = {}
    for column, raw_profile in profiles.items():
        profile = dict(raw_profile)
        series = df[column]
        profile["sample_values"] = _sample_values(series)
        profile["top_values"] = [
            {"value": _json_value(k), "count": int(v)}
            for k, v in series.value_counts(dropna=True).head(8).items()
        ]
        if profile["kind"] == "numeric":
            profile["numeric_profile"] = _numeric_profile(series)
        column_details[column] = profile

    return {
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
        "total_missing_values": int(df.isna().sum().sum()),
        "duplicate_records": int(df.duplicated(keep="first").sum()),
        "columns_with_missing": sum(p["missing_values"] > 0 for p in profiles.values()),
        "numeric_column_names": groups["numeric"],
        "categorical_column_names": groups["categorical"],
        "datetime_column_names": groups["datetime"],
        "identifier_column_names": groups["identifiers"],
        "boolean_column_names": groups["boolean"],
        "null_column_names": groups["null_empty"],
        "columns_with_missing_names": [
            c for c, p in profiles.items() if p["missing_values"] > 0
        ],
        "all_column_names": [str(c) for c in df.columns],
        "column_details": column_details,
        "column_profiles": column_details,
    }
