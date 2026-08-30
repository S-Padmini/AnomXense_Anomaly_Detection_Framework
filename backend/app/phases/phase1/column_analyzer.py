from __future__ import annotations

from typing import Any

import pandas as pd

from .dataset_summary import build_summary
from .column_classifier import classify_dataframe
from app.services.llm_descriptions import generate_column_description


def analyze_dataset(df: pd.DataFrame, filename: str, file_size: int) -> dict[str, Any]:
    summary = build_summary(df, filename, file_size)
    for name, profile in summary["column_details"].items():
        result = generate_column_description(profile, summary)
        profile["description"] = result["description"]
        profile["description_source"] = result["source"]
        profile["description_model"] = result["model"]
    return summary


def get_column_profile(df: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in df.columns:
        raise KeyError(column)
    return classify_dataframe(df)[column]
