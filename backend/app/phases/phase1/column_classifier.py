from __future__ import annotations

import re
from typing import Any

import pandas as pd


# Identifier detection is deliberately conservative. "customer_name" is a
# categorical feature; "customer_id" and "transaction_id" are identifiers.
IDENTIFIER_NAME_RE = re.compile(
    r"(?:^|[_\-\s])(?:id|identifier|uuid|guid|key|code|account_no|account_number|"
    r"customer_id|transaction_id|record_id|reference|ref)(?:$|[_\-\s])",
    re.IGNORECASE,
)
EXACT_IDENTIFIER_NAMES = {
    "id", "uuid", "guid", "identifier", "key", "customerid", "transactionid",
    "recordid", "referenceid", "accountnumber", "account_no", "customer_id",
    "transaction_id", "record_id",
}


def _clean_name(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _is_boolean(series: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(series):
        return True
    values = series.dropna()
    if values.empty or pd.api.types.is_numeric_dtype(series):
        return False
    normalized = {str(v).strip().lower() for v in values.unique()}
    return len(normalized) <= 2 and normalized.issubset(
        {"true", "false", "yes", "no", "0", "1"}
    )


def _datetime_ratio(series: pd.Series) -> float:
    values = series.dropna()
    if values.empty:
        return 0.0
    if pd.api.types.is_datetime64_any_dtype(series):
        return 1.0
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return 0.0
    # Avoid interpreting ordinary short categorical strings as dates.
    sample = values.astype(str).head(100)
    converted = pd.to_datetime(sample, errors="coerce", format="mixed")
    return float(converted.notna().mean())


def _looks_identifier(name: str, series: pd.Series) -> bool:
    values = series.dropna()
    if values.empty:
        return False

    clean = _clean_name(name)
    compact = clean.replace("_", "")
    name_hint = clean in EXACT_IDENTIFIER_NAMES or bool(IDENTIFIER_NAME_RE.search(clean))
    unique_ratio = float(values.nunique(dropna=True) / max(len(values), 1))

    if name_hint and unique_ratio >= 0.80:
        return True

    # UUID-like strings are strong identifiers even without an informative name.
    sample = values.astype(str).head(100)
    uuid_like = sample.str.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    ).mean()
    return bool(uuid_like >= 0.8)


def classify_column(series: pd.Series, name: str) -> dict[str, Any]:
    clean = _clean_name(name)
    missing = int(series.isna().sum())
    non_null = int(series.notna().sum())
    unique = int(series.nunique(dropna=True))
    unique_ratio = float(unique / non_null) if non_null else 0.0

    if non_null == 0:
        kind, role = "null_empty", "Empty Column"
    elif _is_boolean(series):
        kind, role = "boolean", "Boolean Feature"
    elif _looks_identifier(clean, series):
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
        "non_null_values": non_null,
        "unique_values": unique,
        "unique_ratio": round(unique_ratio, 6),
        "is_empty": non_null == 0,
    }


def classify_dataframe(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {str(c): classify_column(df[c], str(c)) for c in df.columns}
