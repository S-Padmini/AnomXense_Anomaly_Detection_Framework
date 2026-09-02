from __future__ import annotations

from typing import Any

import pandas as pd

from .dataset_summary import build_summary
from .column_classifier import classify_dataframe
from app.services.llm_descriptions import generate_column_description


def analyze_dataset(
    df: pd.DataFrame,
    filename: str,
    file_size: int,
) -> dict[str, Any]:
    """
    Phase 1 dataset analysis.

    Responsibilities:
    1. Build complete dataset/profile summary.
    2. Generate a semantic LLM description for every column.
    3. Store the description together with the column profile.

    The LLM receives:
    - column name
    - data type
    - detected role
    - representative values
    - top values
    - numerical characteristics when applicable
    - overall dataset context
    """

    summary = build_summary(
        df=df,
        filename=filename,
        file_size=file_size,
    )

    for column_name, profile in summary["column_details"].items():

        try:
            result = generate_column_description(
                profile=profile,
                dataset_summary=summary,
            )

            profile["description"] = result.get(
                "description",
                "",
            )

            profile["description_source"] = result.get(
                "source",
                "unknown",
            )

            profile["description_model"] = result.get(
                "model",
                None,
            )

        except Exception as exc:
            # Phase 1 should still work if the LLM service
            # temporarily fails.
            profile["description"] = (
                _fallback_column_description(
                    profile,
                    summary,
                )
            )

            profile["description_source"] = "fallback"
            profile["description_model"] = None
            profile["description_error"] = str(exc)

    # Keep both names for compatibility with the existing frontend.
    summary["column_profiles"] = summary["column_details"]

    return summary


def get_column_profile(
    df: pd.DataFrame,
    column: str,
) -> dict[str, Any]:
    """
    Return the classifier profile for a single column.
    """

    if column not in df.columns:
        raise KeyError(column)

    profiles = classify_dataframe(df)

    return profiles[column]


def _fallback_column_description(
    profile: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    """
    Non-LLM fallback.

    This is intentionally semantic rather than simply returning
    statistics such as 'Numeric column with 750 values'.
    """

    name = profile.get("name", "This column")
    role = profile.get("role", "feature")
    kind = profile.get("kind", "unknown")
    sample_values = profile.get("sample_values", [])

    dataset_rows = summary.get("rows", 0)
    dataset_columns = summary.get("columns", 0)

    samples = ", ".join(
        str(value)
        for value in sample_values[:5]
        if value is not None
    )

    if kind == "identifier":
        description = (
            f"'{name}' appears to act as an identifier used to "
            f"distinguish individual records or entities. "
            f"It is generally useful for tracing or grouping "
            f"observations, but should not normally be treated as "
            f"a numerical measurement when building anomaly models."
        )

    elif kind == "datetime":
        description = (
            f"'{name}' is a date/time feature that represents when "
            f"an observation or event occurred. It can provide "
            f"temporal context for detecting changes, unusual timing, "
            f"seasonality, or time-dependent anomalies."
        )

    elif kind == "numeric":
        description = (
            f"'{name}' is a numerical feature representing a "
            f"measurable quantity. Numerical variation in this "
            f"feature can be used to identify unusually large, small, "
            f"or otherwise atypical observations."
        )

    elif kind == "boolean":
        description = (
            f"'{name}' is a boolean-style feature representing a "
            f"binary state or condition. It may provide contextual "
            f"information that helps distinguish normal observations "
            f"from unusual ones."
        )

    elif kind == "categorical":
        description = (
            f"'{name}' is a categorical feature representing "
            f"discrete groups, labels, or states. It can provide "
            f"context for comparing observations within similar "
            f"groups and may be useful for contextual anomaly "
            f"detection."
        )

    elif kind == "null_empty":
        description = (
            f"'{name}' contains no usable non-null observations, "
            f"so its semantic role cannot be reliably determined "
            f"from the available dataset."
        )

    else:
        description = (
            f"'{name}' is classified as a {role.lower()}. "
            f"Its usefulness for anomaly detection depends on how "
            f"its values relate to the other features in the dataset."
        )

    if samples:
        description += (
            f" Representative values include: {samples}."
        )

    description += (
        f" The dataset currently contains {dataset_rows} records "
        f"and {dataset_columns} columns, so this feature should be "
        f"interpreted in the context of the overall dataset."
    )

    return description