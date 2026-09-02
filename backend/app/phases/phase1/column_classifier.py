from __future__ import annotations

import re
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------
# Identifier detection
# ---------------------------------------------------------------------
#
# This is deliberately conservative.
#
# We do NOT classify every column containing words such as "customer"
# or "account" as an identifier.
#
# A column should also have a high uniqueness ratio before being
# classified as an identifier.
# ---------------------------------------------------------------------

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
    "id",
    "uuid",
    "guid",
    "identifier",
    "key",
    "customerid",
    "transactionid",
    "recordid",
    "referenceid",
    "accountnumber",
    "accountno",
    "customer_id",
    "transaction_id",
    "record_id",
}


def _clean_name(name: Any) -> str:
    """
    Normalize a column name for semantic/structural checks.
    """

    return (
        re.sub(
            r"[^a-z0-9]+",
            "_",
            str(name).strip().lower(),
        )
        .strip("_")
    )


def _is_boolean(series: pd.Series) -> bool:
    """
    Detect actual boolean columns and common two-state categorical
    representations.
    """

    if pd.api.types.is_bool_dtype(series):
        return True

    values = series.dropna()

    if values.empty:
        return False

    # Numeric columns should remain numeric even when they contain
    # values such as 0 and 1.
    if pd.api.types.is_numeric_dtype(series):
        return False

    normalized = {
        str(value).strip().lower()
        for value in values.unique()
    }

    return (
        len(normalized) <= 2
        and normalized.issubset(
            {
                "true",
                "false",
                "yes",
                "no",
                "0",
                "1",
            }
        )
    )


def _datetime_ratio(series: pd.Series) -> float:
    """
    Estimate how strongly a column behaves like a date/time feature.
    """

    values = series.dropna()

    if values.empty:
        return 0.0

    if pd.api.types.is_datetime64_any_dtype(series):
        return 1.0

    if (
        pd.api.types.is_numeric_dtype(series)
        or pd.api.types.is_bool_dtype(series)
    ):
        return 0.0

    # Only inspect a representative sample.
    sample = values.astype(str).head(100)

    try:
        converted = pd.to_datetime(
            sample,
            errors="coerce",
            format="mixed",
        )
    except (TypeError, ValueError):
        converted = pd.to_datetime(
            sample,
            errors="coerce",
        )

    return float(converted.notna().mean())


def _looks_identifier(
    name: str,
    series: pd.Series,
) -> bool:
    """
    Determine whether a column is probably an identifier.

    Identifier classification requires either:
    - a strong identifier-style name + high uniqueness
    - a UUID-like value pattern
    """

    values = series.dropna()

    if values.empty:
        return False

    clean = _clean_name(name)

    compact = clean.replace("_", "")

    name_hint = (
        clean in EXACT_IDENTIFIER_NAMES
        or compact in EXACT_IDENTIFIER_NAMES
        or bool(
            IDENTIFIER_NAME_RE.search(clean)
        )
    )

    unique_ratio = float(
        values.nunique(dropna=True)
        / max(len(values), 1)
    )

    # Strong name + strong uniqueness.
    if name_hint and unique_ratio >= 0.80:
        return True

    # UUID-like values.
    sample = values.astype(str).head(100)

    uuid_ratio = float(
        sample.str.fullmatch(
            r"[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}"
        ).mean()
    )

    return uuid_ratio >= 0.80


def classify_column(
    series: pd.Series,
    name: str,
) -> dict[str, Any]:
    """
    Classify a single dataframe column.

    Possible kinds:
        numeric
        categorical
        datetime
        identifier
        boolean
        null_empty
    """

    clean = _clean_name(name)

    missing = int(series.isna().sum())
    non_null = int(series.notna().sum())
    unique = int(series.nunique(dropna=True))

    unique_ratio = (
        float(unique / non_null)
        if non_null
        else 0.0
    )

    # -------------------------------------------------------------
    # Determine semantic kind and role
    # -------------------------------------------------------------

    if non_null == 0:
        kind = "null_empty"
        role = "Empty Column"

    elif _is_boolean(series):
        kind = "boolean"
        role = "Boolean Feature"

    elif _looks_identifier(clean, series):
        kind = "identifier"
        role = "Identifier"

    elif _datetime_ratio(series) >= 0.85:
        kind = "datetime"
        role = "Date / Time Feature"

    elif pd.api.types.is_numeric_dtype(series):
        kind = "numeric"
        role = "Numerical Feature"

    else:
        kind = "categorical"
        role = "Categorical Feature"

    return {
        "name": str(name),
        "dtype": str(series.dtype),
        "kind": kind,
        "role": role,
        "missing_values": missing,
        "missing_percentage": round(
            (
                missing / len(series) * 100
                if len(series)
                else 0.0
            ),
            2,
        ),
        "non_null_values": non_null,
        "unique_values": unique,
        "unique_ratio": round(
            unique_ratio,
            6,
        ),
        "is_empty": non_null == 0,
    }


def classify_dataframe(
    df: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """
    Classify every column in a dataframe.
    """

    return {
        str(column): classify_column(
            df[column],
            str(column),
        )
        for column in df.columns
    }