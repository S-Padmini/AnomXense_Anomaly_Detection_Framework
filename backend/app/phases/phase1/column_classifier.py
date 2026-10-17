from __future__ import annotations

import re
from typing import Any

import pandas as pd


IDENTIFIER_NAME_RE = re.compile(
    r"(?:^|[_\-\s])"
    r"(?:id|identifier|uuid|guid|key|code|"
    r"account[_\-\s]?(?:no|number)|"
    r"customer[_\-\s]?id|"
    r"transaction[_\-\s]?id|"
    r"record[_\-\s]?id|"
    r"reference|ref)"
    r"(?:$|[_\-\s])",
    re.IGNORECASE,
)

EXACT_IDENTIFIER_NAMES = {
    "id", "uuid", "guid", "identifier", "key",
    "customerid", "transactionid", "recordid", "referenceid",
    "accountnumber", "accountno", "customer_id",
    "transaction_id", "record_id",
}

_BOOLEAN_VALUES = {"true", "false", "yes", "no", "0", "1"}


def _clean_name(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _is_boolean(series: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(series):
        return True

    if pd.api.types.is_numeric_dtype(series):
        return False

    values = series.dropna()
    if values.empty:
        return False

    # Avoid building a Python set from millions of values. Two-state
    # detection only needs at most three distinct normalized values.
    try:
        unique_values = values.astype(str).str.strip().str.lower().unique()
        if len(unique_values) > 2:
            return False
        return len(unique_values) <= 2 and set(unique_values).issubset(_BOOLEAN_VALUES)
    except Exception:
        return False


def _datetime_ratio(series: pd.Series) -> float:
    values = series.dropna()
    if values.empty:
        return 0.0

    if pd.api.types.is_datetime64_any_dtype(series):
        return 1.0

    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return 0.0

    # Semantic inference is sampled. It does not need a 10M-row datetime parse.
    sample = values.head(100).astype(str)
    try:
        converted = pd.to_datetime(sample, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        converted = pd.to_datetime(sample, errors="coerce")
    return float(converted.notna().mean())


def _looks_identifier(
    name: str,
    series: pd.Series,
    *,
    unique_ratio: float | None = None,
) -> bool:
    values = series.dropna()
    if values.empty:
        return False

    clean = _clean_name(name)
    compact = clean.replace("_", "")

    name_hint = (
        clean in EXACT_IDENTIFIER_NAMES
        or compact in EXACT_IDENTIFIER_NAMES
        or bool(IDENTIFIER_NAME_RE.search(clean))
    )

    if unique_ratio is None:
        non_null = len(values)
        unique_ratio = (
            float(values.nunique(dropna=True) / non_null)
            if non_null
            else 0.0
        )

    if name_hint and unique_ratio >= 0.80:
        return True

    sample = values.astype(str).head(100)
    try:
        uuid_ratio = float(
            sample.str.fullmatch(
                r"[0-9a-fA-F]{8}-"
                r"[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{12}"
            ).mean()
        )
    except Exception:
        uuid_ratio = 0.0

    return uuid_ratio >= 0.80


def classify_column(
    series: pd.Series,
    name: str,
) -> dict[str, Any]:
    """Backward-compatible single-column classifier."""

    missing = int(series.isna().sum())
    non_null = int(series.notna().sum())
    unique = int(series.nunique(dropna=True))
    unique_ratio = float(unique / non_null) if non_null else 0.0

    if non_null == 0:
        kind, role = "null_empty", "Empty Column"
    elif _is_boolean(series):
        kind, role = "boolean", "Boolean Feature"
    elif _looks_identifier(name, series, unique_ratio=unique_ratio):
        kind, role = "identifier", "Identifier"
    elif _datetime_ratio(series) >= 0.85:
        kind, role = "datetime", "Date / Time Feature"
    elif pd.api.types.is_numeric_dtype(series):
        kind, role = "numeric", "Numerical Feature"
    else:
        kind, role = "categorical", "Categorical Feature"

    return {
        "name": str(name),
        "dtype": str(series.dtype),
        "kind": kind,
        "role": role,
        "missing_values": missing,
        "missing_percentage": round(missing / len(series) * 100 if len(series) else 0.0, 2),
        "non_null_values": non_null,
        "unique_values": unique,
        "unique_ratio": round(unique_ratio, 6),
        "is_empty": non_null == 0,
    }


def classify_dataframe(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """
    Classify all columns while sharing the expensive dataframe-wide
    missing/unique computations.

    This preserves the existing output contract but removes repeated
    isna()/notna()/nunique() passes from identifier detection.
    """
    if df.empty:
        return {}

    missing_counts = df.isna().sum()
    non_null_counts = len(df) - missing_counts
    unique_counts = df.nunique(dropna=True)

    profiles: dict[str, dict[str, Any]] = {}

    for column in df.columns:
        name = str(column)
        series = df[column]
        missing = int(missing_counts[column])
        non_null = int(non_null_counts[column])
        unique = int(unique_counts[column])
        unique_ratio = float(unique / non_null) if non_null else 0.0

        if non_null == 0:
            kind, role = "null_empty", "Empty Column"
        elif _is_boolean(series):
            kind, role = "boolean", "Boolean Feature"
        elif _looks_identifier(name, series, unique_ratio=unique_ratio):
            kind, role = "identifier", "Identifier"
        elif _datetime_ratio(series) >= 0.85:
            kind, role = "datetime", "Date / Time Feature"
        elif pd.api.types.is_numeric_dtype(series):
            kind, role = "numeric", "Numerical Feature"
        else:
            kind, role = "categorical", "Categorical Feature"

        profiles[name] = {
            "name": name,
            "dtype": str(series.dtype),
            "kind": kind,
            "role": role,
            "missing_values": missing,
            "missing_percentage": round(
                missing / len(df) * 100 if len(df) else 0.0, 2
            ),
            "non_null_values": non_null,
            "unique_values": unique,
            "unique_ratio": round(unique_ratio, 6),
            "is_empty": non_null == 0,
        }

    return profiles
