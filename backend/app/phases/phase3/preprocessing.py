from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if not isinstance(result, (list, tuple, np.ndarray, pd.Series)) else False
    except Exception:
        return False


def _json_value(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _numeric_values(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def _skewness(series: pd.Series) -> float:
    nums = _numeric_values(series)
    if len(nums) < 3:
        return 0.0
    value = float(nums.skew())
    return value if np.isfinite(value) else 0.0


def _format_number(value: float | None) -> float | int | None:
    if value is None or not np.isfinite(float(value)):
        return None
    rounded = round(float(value), 6)
    return int(rounded) if rounded.is_integer() else rounded


def _identifier_column(summary: dict[str, Any], selected: list[str]) -> str | None:
    for column in summary.get("identifier_column_names", []):
        if column in selected:
            return column
    # If the identifier was not selected, use any available identifier solely
    # to identify affected rows in the UI.
    for column in summary.get("identifier_column_names", []):
        return column
    return None


def _row_ref(index: Any, row: pd.Series, identifier: str | None) -> dict[str, Any]:
    item = {"index": _json_value(index)}
    if identifier:
        item["identifier_column"] = identifier
        item["identifier"] = _json_value(row.get(identifier))
    return item


def _missing_records(df: pd.DataFrame, column: str, identifier: str | None) -> list[dict[str, Any]]:
    return [
        _row_ref(idx, row, identifier) | {"value": None}
        for idx, row in df.loc[df[column].isna()].iterrows()
    ]


def _duplicate_value_records(df: pd.DataFrame, column: str, identifier: str | None) -> list[dict[str, Any]]:
    series = df[column]
    mask = series.notna() & series.duplicated(keep=False)
    groups = []
    for value, group in df.loc[mask].groupby(column, dropna=False, sort=False):
        groups.append({
            "value": _json_value(value),
            "records": [_row_ref(idx, row, identifier) for idx, row in group.iterrows()],
        })
    return groups


def _exact_duplicate_records(df: pd.DataFrame, columns: list[str], identifier: str | None) -> list[dict[str, Any]]:
    # Every selected column participates. Keep the first copy and report each
    # later exact duplicate as a removed record. Build stable Python keys so
    # missing values compare equal (pandas' NaN == NaN is False).
    def key_for(row: pd.Series) -> tuple[Any, ...]:
        return tuple(None if _is_missing(row[c]) else str(row[c]) for c in columns)

    first_index_by_key: dict[tuple[Any, ...], Any] = {}
    records = []
    for idx, row in df.iterrows():
        key = key_for(row)
        if key not in first_index_by_key:
            first_index_by_key[key] = idx
            continue
        item = _row_ref(idx, row, identifier)
        item["duplicate_of"] = _json_value(first_index_by_key[key])
        records.append(item)
    return records


def build_preprocessing_inspection(
    df: pd.DataFrame, selected_columns: list[str], summary: dict[str, Any]
) -> dict[str, Any]:
    identifier = _identifier_column(summary, selected_columns)
    columns = []
    for column in selected_columns:
        series = df[column]
        columns.append({
            "column": column,
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            # This is repeated cell count, not exact duplicate row count.
            "duplicate_values": int(series.dropna().duplicated(keep=False).sum()),
            "missing_records": _missing_records(df, column, identifier),
            "duplicate_records": _duplicate_value_records(df, column, identifier),
        })

    exact_mask = df.duplicated(subset=selected_columns, keep="first")
    return {
        "row_count": int(len(df)),
        "columns": columns,
        "missingTotal": int(df[selected_columns].isna().sum().sum()),
        "exactDuplicateRows": int(exact_mask.sum()),
        "duplicateValueTotal": int(sum(x["duplicate_values"] for x in columns)),
        "allMissingRecords": [
            {"column": c, "records": _missing_records(df, c, identifier)}
            for c in selected_columns if df[c].isna().any()
        ],
        "allDuplicateRecords": _exact_duplicate_records(df, selected_columns, identifier),
    }


def _action_text(action: dict[str, Any], numeric: bool) -> str:
    method = action["method"]
    if method in {"No missing values", "No usable numeric values"}:
        return method
    if numeric and action.get("skewness") is not None:
        return f'{method} (skewness {float(action["skewness"]):.2f})'
    filled = action.get("filled_value")
    return f"{method} ({filled})"


def preprocess_dataset(
    df: pd.DataFrame, selected_columns: list[str], summary: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not selected_columns:
        raise ValueError("At least one column must be selected.")

    work = df.copy()
    before_rows = len(work)

    # IMPORTANT: exact duplicates are determined from the original selected
    # data, before imputation, so imputation cannot accidentally create a new
    # duplicate and remove a legitimate record.
    duplicate_mask = work.duplicated(subset=selected_columns, keep="first")
    duplicate_count = int(duplicate_mask.sum())
    identifier = _identifier_column(summary, selected_columns)
    duplicate_records = _exact_duplicate_records(work, selected_columns, identifier)
    work = work.loc[~duplicate_mask].copy()

    before_missing = int(work[selected_columns].isna().sum().sum())
    actions: dict[str, dict[str, Any]] = {}
    numeric_set = set(summary.get("numeric_column_names", []))
    datetime_set = set(summary.get("datetime_column_names", []))
    boolean_set = set(summary.get("boolean_column_names", []))

    for column in selected_columns:
        series = work[column]
        missing_count = int(series.isna().sum())
        skew = _skewness(series) if column in numeric_set else None

        if missing_count == 0:
            actions[column] = {
                "method": "No missing values",
                "skewness": _format_number(skew),
                "filled_value": None,
                "missing_values_handled": 0,
            }
            continue

        if column in numeric_set:
            nums = _numeric_values(series)
            if nums.empty:
                method, fill_value = "No usable numeric values", None
            else:
                method = "Mean imputation" if abs(skew or 0) <= 0.5 else "Median imputation"
                fill_value = float(nums.mean() if method == "Mean imputation" else nums.median())
                work[column] = series.fillna(fill_value)
        elif column in datetime_set:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            mode = parsed.dropna().mode()
            fill_value = mode.iloc[0] if not mode.empty else None
            if fill_value is not None:
                work[column] = parsed.fillna(fill_value)
            method = "Date/Time mode imputation"
        else:
            mode = series.dropna().mode()
            fill_value = mode.iloc[0] if not mode.empty else None
            if fill_value is not None:
                work[column] = series.fillna(fill_value)
            method = "Boolean mode imputation" if column in boolean_set else "Mode imputation"

        actions[column] = {
            "method": method,
            "skewness": _format_number(skew),
            "filled_value": _json_value(fill_value),
            "missing_values_handled": missing_count,
        }

    after_missing = int(work[selected_columns].isna().sum().sum())
    work.index.name = "index"

    action_text = {
        c: _action_text(a, c in numeric_set) for c, a in actions.items()
    }
    result = {
        "success": True,
        "message": "Preprocessing completed successfully",
        "before": {
            "rows": before_rows,
            "columns": len(selected_columns),
            "missing_values": before_missing,
            "duplicate_records": duplicate_count,
        },
        "after": {
            "rows": int(len(work)),
            "columns": len(selected_columns),
            "missing_values": after_missing,
            "duplicate_records": 0,
        },
        "missing_values_handled": before_missing - after_missing,
        "duplicate_records_removed": duplicate_count,
        "columns_removed": [],
        "extreme_values_retained": True,
        "actions": actions,
        "action_text": action_text,
        "duplicate_records": duplicate_records,
        "selected_columns": selected_columns,
        "rows": _dataframe_to_records(work[selected_columns]),
        "index_name": "index",
    }
    return work, result


def _dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for idx, row in df.iterrows():
        item = {"__index": _json_value(idx)}
        item.update({str(c): _json_value(row[c]) for c in df.columns})
        rows.append(item)
    return rows
