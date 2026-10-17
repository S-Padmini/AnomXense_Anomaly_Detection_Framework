from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from .dataset_summary import build_summary
from .column_classifier import classify_dataframe
from app.services.llm_descriptions import (
    build_dataset_semantic_context,
    generate_column_description,
)


def _max_llm_workers(column_count: int) -> int:
    """Bound concurrency so large schemas do not flood the LLM provider."""
    configured = os.getenv("PHASE1_LLM_WORKERS", "4")
    try:
        workers = max(1, int(configured))
    except ValueError:
        workers = 4
    return min(workers, max(1, column_count))


def _describe_one(
    column_name: str,
    profile: dict[str, Any],
    summary: dict[str, Any],
    semantic_context: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    try:
        result = generate_column_description(
            profile=profile,
            dataset_summary=summary,
            semantic_context=semantic_context,
        )

        profile["description"] = result.get("description", "") or ""
        profile["description_source"] = result.get("source", "unknown")
        profile["description_model"] = result.get("model")
        if result.get("error"):
            profile["description_error"] = str(result["error"])

    except Exception as exc:
        profile["description"] = _fallback_column_description(profile, summary)
        profile["description_source"] = "fallback"
        profile["description_model"] = None
        profile["description_error"] = str(exc)

    return column_name, profile


def analyze_dataset(
    df: pd.DataFrame,
    filename: str,
    file_size: int,
) -> dict[str, Any]:
    """
    Phase 1 dataset analysis.

    The important optimization is that semantic dataset context is built ONCE.
    The old implementation rebuilt it for every column and recalculated full
    dataframe correlations and value statistics repeatedly.
    """
    summary = build_summary(
        df=df,
        filename=filename,
        file_size=file_size,
    )

    column_details = summary["column_details"]

    # Build semantic evidence once. It is reused by every LLM request.
    semantic_context = build_dataset_semantic_context(
        df=df,
        target_column="",
        dataset_summary=summary,
    )

    workers = _max_llm_workers(len(column_details))

    if workers == 1:
        for column_name, profile in column_details.items():
            _, updated = _describe_one(
                column_name, profile, summary, semantic_context
            )
            column_details[column_name] = updated
    else:
        # Preserve column order while allowing independent LLM calls to run
        # concurrently. Each result is written back to its original profile.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _describe_one,
                    column_name,
                    profile,
                    summary,
                    semantic_context,
                ): column_name
                for column_name, profile in column_details.items()
            }

            for future in as_completed(futures):
                column_name = futures[future]
                try:
                    _, updated = future.result()
                except Exception as exc:
                    updated = dict(column_details[column_name])
                    updated["description"] = _fallback_column_description(
                        updated, summary
                    )
                    updated["description_source"] = "fallback"
                    updated["description_model"] = None
                    updated["description_error"] = str(exc)

                column_details[column_name] = updated

    summary["column_profiles"] = summary["column_details"]
    return summary


def get_column_profile(df: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in df.columns:
        raise KeyError(column)
    profiles = classify_dataframe(df)
    return profiles[column]


def _fallback_column_description(
    profile: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    name = profile.get("name", "This column")
    role = profile.get("role", "feature")
    kind = profile.get("kind", "unknown")
    sample_values = profile.get("sample_values", [])

    dataset_rows = summary.get("rows", 0)
    dataset_columns = summary.get("columns", 0)

    samples = ", ".join(
        str(value) for value in sample_values[:5] if value is not None
    )

    if kind == "identifier":
        description = (
            f"'{name}' appears to act as an identifier used to "
            f"distinguish individual records or entities. It is generally "
            f"useful for tracing or grouping observations, but should not "
            f"normally be treated as a numerical measurement when building "
            f"anomaly models."
        )
    elif kind == "datetime":
        description = (
            f"'{name}' is a date/time feature that represents when an "
            f"observation or event occurred. It can provide temporal context "
            f"for detecting changes, unusual timing, seasonality, or "
            f"time-dependent anomalies."
        )
    elif kind == "numeric":
        description = (
            f"'{name}' is a numerical feature representing a measurable "
            f"quantity. Numerical variation in this feature can be used to "
            f"identify unusually large, small, or otherwise atypical "
            f"observations."
        )
    elif kind == "boolean":
        description = (
            f"'{name}' is a boolean-style feature representing a binary "
            f"state or condition. It may provide contextual information "
            f"that helps distinguish normal observations from unusual ones."
        )
    elif kind == "categorical":
        description = (
            f"'{name}' is a categorical feature representing discrete "
            f"groups, labels, or states. It can provide context for "
            f"comparing observations within similar groups and may be "
            f"useful for contextual anomaly detection."
        )
    elif kind == "null_empty":
        description = (
            f"'{name}' contains no usable non-null observations, so its "
            f"semantic role cannot be reliably determined from the "
            f"available dataset."
        )
    else:
        description = (
            f"'{name}' is classified as a {role.lower()}. Its usefulness "
            f"for anomaly detection depends on how its values relate to "
            f"the other features in the dataset."
        )

    if samples:
        description += f" Representative values include: {samples}."

    description += (
        f" The dataset currently contains {dataset_rows} records and "
        f"{dataset_columns} columns, so this feature should be interpreted "
        f"in the context of the overall dataset."
    )
    return description
