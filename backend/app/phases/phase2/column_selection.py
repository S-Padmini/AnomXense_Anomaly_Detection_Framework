from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.llm_descriptions import (
    generate_column_description,
)


# =========================================================
# VALIDATE SELECTION
# =========================================================

def validate_selection(
    df: pd.DataFrame,
    selected_columns: list[str],
) -> list[str]:

    available = [
        str(c)
        for c in df.columns
    ]

    if not selected_columns:
        raise ValueError(
            "Select at least one column."
        )

    unknown = [
        c
        for c in selected_columns
        if c not in available
    ]

    if unknown:
        raise ValueError(
            f"Unknown columns: {', '.join(unknown)}"
        )

    wanted = set(
        selected_columns
    )

    return [
        c
        for c in available
        if c in wanted
    ]


# =========================================================
# BUILD SELECTION RESPONSE
# =========================================================

def build_selection_response(
    df: pd.DataFrame,
    summary: dict[str, Any],
    selected_columns: list[str],
) -> dict[str, Any]:

    selected = validate_selection(
        df,
        selected_columns,
    )

    return {
        "selected_columns": selected,

        "selected_count": len(
            selected
        ),

        "total_columns": len(
            df.columns
        ),

        "selected_column_details": {
            c: summary[
                "column_details"
            ][c]
            for c in selected
        },
    }


# =========================================================
# DESCRIBE COLUMN ON DEMAND
# =========================================================

def describe_column_on_demand(
    df: pd.DataFrame,
    summary: dict[str, Any],
    column: str,
) -> dict[str, Any]:

    if column not in df.columns:
        raise KeyError(column)

    # -----------------------------------------------------
    # Existing backend profile
    # -----------------------------------------------------

    profile = dict(
        summary[
            "column_details"
        ].get(
            column,
            {},
        )
    )

    # Always make the actual dataframe column name
    # available to the semantic service.

    profile["name"] = column

    # -----------------------------------------------------
    # Generate semantic description
    #
    # The COMPLETE dataframe is passed to the LLM service.
    # Therefore the LLM can reason using other columns,
    # representative values and numeric relationships.
    # -----------------------------------------------------

    result = generate_column_description(
        profile=profile,
        dataset_summary=summary,
        df=df,
        use_llm=True,
    )

    # -----------------------------------------------------
    # Preserve existing profile fields.
    #
    # Add only the description metadata required by
    # the frontend.
    # -----------------------------------------------------

    profile.update(
        description=result.get(
            "description"
        ),

        description_source=result.get(
            "source"
        ),

        description_model=result.get(
            "model"
        ),

        description_error=result.get(
            "error"
        ),
    )

    return profile

