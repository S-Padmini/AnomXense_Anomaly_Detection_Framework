from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .column_classifier import classify_dataframe


def _json_value(value: Any) -> Any:
    """
    Convert pandas/numpy values into JSON-safe Python values.
    """

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


def _sample_values(
    series: pd.Series,
    limit: int = 12,
) -> list[Any]:
    """
    Representative non-null values used by the LLM
    for semantic column interpretation.
    """

    return [
        _json_value(value)
        for value in series.dropna()
        .head(limit)
        .tolist()
    ]


def _numeric_profile(
    series: pd.Series,
) -> dict[str, Any]:
    """
    Numerical characteristics retained for internal analysis
    and LLM context.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if numeric.empty:
        return {}

    return {
        "min": _json_value(
            numeric.min()
        ),
        "max": _json_value(
            numeric.max()
        ),
        "mean": _json_value(
            numeric.mean()
        ),
        "median": _json_value(
            numeric.median()
        ),
        "std": (
            _json_value(
                numeric.std(ddof=1)
            )
            if len(numeric) > 1
            else 0.0
        ),
    }


def build_summary(
    df: pd.DataFrame,
    filename: str,
    file_size: int,
) -> dict[str, Any]:
    """
    Build the complete Phase 1 dataset summary.

    The summary is intentionally rich internally because later
    phases need dataset context.

    The frontend can choose which pieces to display.
    """

    profiles = classify_dataframe(df)

    # -------------------------------------------------------------
    # Group columns by detected semantic kind
    # -------------------------------------------------------------

    groups = {
        "numeric": [
            column
            for column, profile in profiles.items()
            if profile["kind"] == "numeric"
        ],

        "categorical": [
            column
            for column, profile in profiles.items()
            if profile["kind"] == "categorical"
        ],

        "datetime": [
            column
            for column, profile in profiles.items()
            if profile["kind"] == "datetime"
        ],

        "identifiers": [
            column
            for column, profile in profiles.items()
            if profile["kind"] == "identifier"
        ],

        "boolean": [
            column
            for column, profile in profiles.items()
            if profile["kind"] == "boolean"
        ],

        "null_empty": [
            column
            for column, profile in profiles.items()
            if profile["kind"] == "null_empty"
        ],
    }

    # -------------------------------------------------------------
    # Build detailed column information
    # -------------------------------------------------------------

    column_details: dict[str, Any] = {}

    for column, raw_profile in profiles.items():

        profile = dict(raw_profile)

        series = df[column]

        # Representative values for semantic LLM analysis.
        profile["sample_values"] = _sample_values(
            series
        )

        # Most common values are useful for understanding
        # categorical columns.
        profile["top_values"] = [
            {
                "value": _json_value(key),
                "count": int(value_count),
            }
            for key, value_count
            in series.value_counts(
                dropna=True
            ).head(8).items()
        ]

        # Numerical information is available internally when
        # the column is numerical.
        if profile["kind"] == "numeric":
            profile["numeric_profile"] = (
                _numeric_profile(series)
            )

        column_details[column] = profile

    # -------------------------------------------------------------
    # Dataset-level summary
    # -------------------------------------------------------------

    total_rows = int(len(df))
    total_columns = int(len(df.columns))
    total_missing = int(
        df.isna().sum().sum()
    )

    duplicate_records = int(
        df.duplicated(
            keep="first"
        ).sum()
    )

    columns_with_missing = [
        column
        for column, profile
        in profiles.items()
        if profile["missing_values"] > 0
    ]

    summary = {
        "dataset_id": None,

        "filename": filename,

        "file_size_bytes": int(file_size),

        "file_size_mb": round(
            file_size / (1024 * 1024),
            2,
        ),

        # Core dataset dimensions
        "rows": total_rows,
        "columns": total_columns,

        # Feature composition
        "numeric": len(
            groups["numeric"]
        ),

        "categorical": len(
            groups["categorical"]
        ),

        "datetime": len(
            groups["datetime"]
        ),

        "identifiers": len(
            groups["identifiers"]
        ),

        "boolean": len(
            groups["boolean"]
        ),

        "null_empty": len(
            groups["null_empty"]
        ),

        # Data quality
        "total_missing_values": total_missing,

        "duplicate_records": duplicate_records,

        "columns_with_missing": len(
            columns_with_missing
        ),

        # Column names
        "numeric_column_names": groups[
            "numeric"
        ],

        "categorical_column_names": groups[
            "categorical"
        ],

        "datetime_column_names": groups[
            "datetime"
        ],

        "identifier_column_names": groups[
            "identifiers"
        ],

        "boolean_column_names": groups[
            "boolean"
        ],

        "null_column_names": groups[
            "null_empty"
        ],

        "columns_with_missing_names":
            columns_with_missing,

        "all_column_names": [
            str(column)
            for column in df.columns
        ],

        # Detailed profiles
        "column_details": column_details,

        # Backward compatibility with existing code
        "column_profiles": column_details,
    }

    return summary