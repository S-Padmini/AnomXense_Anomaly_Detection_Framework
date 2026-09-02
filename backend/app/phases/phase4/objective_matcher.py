from __future__ import annotations

from typing import Any


def _profile_type(profile: dict[str, Any]) -> str:
    return str(
        profile.get("type")
        or profile.get("data_type")
        or profile.get("dtype")
        or ""
    ).lower()


def _is_numeric(profile: dict[str, Any]) -> bool:
    value = _profile_type(profile)

    return any(
        token in value
        for token in (
            "int",
            "float",
            "double",
            "decimal",
            "numeric",
        )
    )


def _is_temporal(profile: dict[str, Any]) -> bool:
    value = _profile_type(profile)

    return any(
        token in value
        for token in (
            "date",
            "time",
            "datetime",
            "timestamp",
        )
    )


def _safe_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def validate_objective_match(
    *,
    interpretation: dict[str, Any],
    selected_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
    phase3_statistics: dict[str, Any],
) -> dict[str, Any]:

    selected = set(selected_columns)

    warnings = list(
        interpretation.get("warnings", [])
    )

    assumptions = list(
        interpretation.get("assumptions", [])
    )

    valid_target = []
    valid_reference = []
    valid_context = []

    for item in interpretation.get(
        "target_columns",
        [],
    ):
        column = item.get("column")

        if column in selected:
            valid_target.append(item)

    for item in interpretation.get(
        "reference_columns",
        [],
    ):
        column = item.get("column")

        if column in selected:
            valid_reference.append(item)

    for item in interpretation.get(
        "context_columns",
        [],
    ):
        column = item.get("column")

        if column in selected:
            valid_context.append(item)

    # A target should normally exist for point-style numerical
    # detection. However, we do not reject the objective because
    # collective/contextual objectives may be expressed without a
    # directly named target.
    if not valid_target:
        warnings.append(
            "No sufficiently confident target column was identified "
            "from the selected columns."
        )

    # Check temporal requirement against actual selected columns.
    temporal_columns = [
        column
        for column in selected_columns
        if _is_temporal(
            column_profiles.get(column, {})
        )
    ]

    temporal_requirement = interpretation.get(
        "temporal_requirement",
        "unclear",
    )

    if (
        temporal_requirement == "required"
        and not temporal_columns
    ):
        warnings.append(
            "The objective requires temporal behavior, but no "
            "selected temporal column was identified."
        )

    if (
        temporal_requirement == "required"
        and temporal_columns
    ):
        assumptions.append(
            "Temporal behavior can be analyzed using the selected "
            f"temporal column(s): {', '.join(temporal_columns)}."
        )

    # Local comparison should have some reference/context evidence.
    if (
        interpretation.get("comparison_scope") == "local"
        and not valid_reference
        and not valid_context
    ):
        warnings.append(
            "The objective implies local comparison, but no "
            "reference/context column was confidently identified."
        )

    # Validate target suitability where possible.
    for item in valid_target:
        profile = column_profiles.get(
            item["column"],
            {},
        )

        if not _is_numeric(profile):
            assumptions.append(
                f"Target column '{item['column']}' is not "
                "classified as numeric. Model suitability will "
                "account for this."
            )

    # Validate collective behavior against available evidence.
    if interpretation.get("anomaly_type") == "collective":
        if not phase3_statistics:
            warnings.append(
                "Collective anomaly interpretation has limited "
                "statistical evidence because Phase 3 statistics "
                "are unavailable."
            )

    interpretation = {
        **interpretation,
        "target_columns": valid_target,
        "reference_columns": valid_reference,
        "context_columns": valid_context,
        "assumptions": list(dict.fromkeys(assumptions)),
        "warnings": list(dict.fromkeys(warnings)),
    }

    return interpretation


def objective_feature_summary(
    interpretation: dict[str, Any],
) -> dict[str, Any]:

    target_count = len(
        interpretation.get("target_columns", [])
    )

    reference_count = len(
        interpretation.get("reference_columns", [])
    )

    context_count = len(
        interpretation.get("context_columns", [])
    )

    return {
        "anomaly_type": interpretation.get(
            "anomaly_type",
            "point",
        ),
        "comparison_scope": interpretation.get(
            "comparison_scope",
            "none",
        ),
        "detection_behavior": interpretation.get(
            "detection_behavior",
            "",
        ),
        "temporal_requirement": interpretation.get(
            "temporal_requirement",
            "unclear",
        ),
        "target_count": target_count,
        "reference_count": reference_count,
        "context_count": context_count,
        "target_columns": [
            item["column"]
            for item in interpretation.get(
                "target_columns",
                [],
            )
        ],
        "reference_columns": [
            item["column"]
            for item in interpretation.get(
                "reference_columns",
                [],
            )
        ],
        "context_columns": [
            item["column"]
            for item in interpretation.get(
                "context_columns",
                [],
            )
        ],
    }