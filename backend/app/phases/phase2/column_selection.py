from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.llm_descriptions import generate_column_description


def validate_selection(df: pd.DataFrame, selected_columns: list[str]) -> list[str]:
    available = [str(c) for c in df.columns]
    if not selected_columns:
        raise ValueError("Select at least one column.")
    unknown = [c for c in selected_columns if c not in available]
    if unknown:
        raise ValueError(f"Unknown columns: {', '.join(unknown)}")
    wanted = set(selected_columns)
    return [c for c in available if c in wanted]


def build_selection_response(df: pd.DataFrame, summary: dict[str, Any],
                             selected_columns: list[str]) -> dict[str, Any]:
    selected = validate_selection(df, selected_columns)
    return {
        "selected_columns": selected,
        "selected_count": len(selected),
        "total_columns": len(df.columns),
        "selected_column_details": {
            c: summary["column_details"][c] for c in selected
        },
    }


def describe_column_on_demand(df: pd.DataFrame, summary: dict[str, Any],
                              column: str) -> dict[str, Any]:
    if column not in df.columns:
        raise KeyError(column)
    profile = dict(summary["column_details"][column])
    result = generate_column_description(profile, summary)
    profile.update(
        description=result["description"],
        description_source=result["source"],
        description_model=result["model"],
    )
    return profile
