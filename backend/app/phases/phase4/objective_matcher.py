from __future__ import annotations

from typing import Any


# ============================================================
# PROFILE HELPERS
# ============================================================

def _profile_type(
    profile: dict[str, Any],
) -> str:

    return str(
        profile.get("type")
        or profile.get("data_type")
        or profile.get("dtype")
        or ""
    ).lower()


def _is_temporal(
    profile: dict[str, Any],
) -> bool:

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


def _safe_confidence(
    value: Any,
) -> float:

    try:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )
    except (TypeError, ValueError):
        return 0.0


# ============================================================
# DEDUPLICATION
# ============================================================

def _deduplicate_columns(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    result: dict[str, dict[str, Any]] = {}

    for item in items:

        column = item.get("column")

        if not column:
            continue

        confidence = _safe_confidence(
            item.get("confidence")
        )

        if (
            column not in result
            or confidence
            > _safe_confidence(
                result[column].get("confidence")
            )
        ):
            result[column] = item

    return list(
        result.values()
    )


# ============================================================
# ROLE VALIDATION
# ============================================================

def _validate_role(
    *,
    interpretation: dict[str, Any],
    role: str,
    selected_columns: set[str],
) -> list[dict[str, Any]]:

    valid: list[dict[str, Any]] = []

    items = interpretation.get(
        f"{role}_columns",
        [],
    )

    if not isinstance(items, list):
        return valid

    for item in items:

        if not isinstance(item, dict):
            continue

        column = str(
            item.get(
                "column",
                "",
            )
        ).strip()

        if not column:
            continue

        if column not in selected_columns:
            continue

        confidence = _safe_confidence(
            item.get("confidence")
        )

        evidence = str(
            item.get(
                "evidence",
                "",
            )
        ).strip()

        valid.append(
            {
                "column": column,
                "role": role,
                "confidence": confidence,
                "evidence": evidence,
            }
        )

    return _deduplicate_columns(valid)


# ============================================================
# DETECTION COLUMN VALIDATION
# ============================================================

def _validate_detection_columns(
    interpretation: dict[str, Any],
    selected_columns: set[str],
) -> list[dict[str, Any]]:

    items = interpretation.get(
        "target_columns",
        [],
    )

    if not isinstance(items, list):
        return []

    valid: list[dict[str, Any]] = []

    allowed_roles = {
        "detection_feature",
        "context_feature",
        "entity_identifier",
        "reference_feature",
        "temporal_feature",
    }

    for item in items:

        if not isinstance(item, dict):
            continue

        column = str(
            item.get(
                "column",
                "",
            )
        ).strip()

        if not column:
            continue

        if column not in selected_columns:
            continue

        confidence = _safe_confidence(
            item.get("confidence")
        )

        evidence = str(
            item.get(
                "evidence",
                "",
            )
        ).strip()

        role = str(
            item.get(
                "role",
                "detection_feature",
            )
        ).strip().lower()

        if role not in allowed_roles:
            role = "detection_feature"

        valid.append(
            {
                "column": column,
                "role": role,
                "confidence": confidence,
                "evidence": evidence,
            }
        )

    return _deduplicate_columns(valid)


# ============================================================
# OBJECTIVE ATTRIBUTE EXTRACTION
# ============================================================

def _objective_attributes(
    interpretation: dict[str, Any],
) -> list[dict[str, Any]]:

    items = interpretation.get(
        "attributes_involved",
        [],
    )

    if not isinstance(items, list):
        return []

    result: list[dict[str, Any]] = []

    for item in items:

        if isinstance(item, str):

            column = item.strip()

            if not column:
                continue

            result.append(
                {
                    "column": column,
                    "role": "supporting_feature",
                    "confidence": 0.0,
                    "reason": "",
                }
            )

            continue

        if not isinstance(item, dict):
            continue

        column = str(
            item.get("column")
            or item.get("name")
            or item.get("column_name")
            or ""
        ).strip()

        if not column:
            continue

        role = str(
            item.get(
                "role",
                "supporting_feature",
            )
        ).strip().lower()

        role_aliases = {
            "target": "detection_feature",
            "detection": "detection_feature",
            "detection_feature": "detection_feature",
            "entity": "entity_identifier",
            "entity_identifier": "entity_identifier",
            "reference": "reference_feature",
            "reference_feature": "reference_feature",
            "context": "context_feature",
            "context_feature": "context_feature",
            "temporal": "temporal_feature",
            "temporal_feature": "temporal_feature",
            "supporting": "supporting_feature",
            "supporting_feature": "supporting_feature",
        }

        role = role_aliases.get(
            role,
            "supporting_feature",
        )

        result.append(
            {
                "column": column,
                "role": role,
                "confidence": _safe_confidence(
                    item.get("confidence")
                ),
                "reason": str(
                    item.get("reason")
                    or item.get("evidence")
                    or item.get("explanation")
                    or item.get("why_relevant")
                    or ""
                ).strip(),
            }
        )

    return _deduplicate_columns(result)


# ============================================================
# ATTRIBUTE SELECTION VALIDATION
# ============================================================

def _validate_attribute_selection(
    *,
    interpretation: dict[str, Any],
    selected_columns: list[str],
) -> tuple[
    list[dict[str, Any]],
    list[str],
    bool,
]:

    selected_set = {
        str(column).strip()
        for column in selected_columns
        if str(column).strip()
    }

    objective_attributes = _objective_attributes(
        interpretation
    )

    missing: list[str] = []

    for item in objective_attributes:

        column = item.get("column")

        if not column:
            continue

        if column not in selected_set:
            missing.append(column)

    missing = list(
        dict.fromkeys(missing)
    )

    return (
        objective_attributes,
        missing,
        len(missing) == 0,
    )


# ============================================================
# MAIN VALIDATION
# ============================================================

def validate_objective_match(
    *,
    interpretation: dict[str, Any],
    selected_columns: list[str],
    column_profiles: dict[str, dict[str, Any]],
    phase3_statistics: dict[str, Any],
) -> dict[str, Any]:

    selected = set(
        selected_columns
    )

    warnings = list(
        interpretation.get(
            "warnings",
            [],
        )
    )

    assumptions = list(
        interpretation.get(
            "assumptions",
            [],
        )
    )

    # --------------------------------------------------------
    # OBJECTIVE ATTRIBUTE VALIDATION
    # --------------------------------------------------------

    objective_attributes, missing_attributes, selection_valid = (
        _validate_attribute_selection(
            interpretation=interpretation,
            selected_columns=selected_columns,
        )
    )

    # --------------------------------------------------------
    # COLUMNS RECOMMENDED FOR DETECTION
    # --------------------------------------------------------

    valid_detection = _validate_detection_columns(
        interpretation,
        selected,
    )

    valid_target = valid_detection

    # --------------------------------------------------------
    # REFERENCE COLUMNS
    # --------------------------------------------------------

    valid_reference = _validate_role(
        interpretation=interpretation,
        role="reference",
        selected_columns=selected,
    )

    # --------------------------------------------------------
    # CONTEXT COLUMNS
    # --------------------------------------------------------

    valid_context = _validate_role(
        interpretation=interpretation,
        role="context",
        selected_columns=selected,
    )

    # --------------------------------------------------------
    # DETECTION WARNING
    # --------------------------------------------------------

    if not valid_detection:

        warnings.append(
            "No sufficiently confident column was identified "
            "for the stated detection objective from the "
            "selected columns."
        )

    # --------------------------------------------------------
    # TEMPORAL VALIDATION
    # --------------------------------------------------------

    temporal_columns = [
        column
        for column in selected_columns
        if _is_temporal(
            column_profiles.get(
                column,
                {},
            )
        )
    ]

    temporal_requirement = str(
        interpretation.get(
            "temporal_requirement",
            "unclear",
        )
    ).lower()

    if (
        temporal_requirement == "required"
        and not temporal_columns
    ):

        warnings.append(
            "The objective requires temporal analysis, "
            "but no selected temporal column is available."
        )

    if (
        temporal_requirement == "required"
        and temporal_columns
    ):

        assumptions.append(
            "Temporal behavior can be analyzed using "
            "the selected temporal column(s): "
            + ", ".join(temporal_columns)
            + "."
        )

    # --------------------------------------------------------
    # LOCAL COMPARISON VALIDATION
    # --------------------------------------------------------

    comparison_scope = str(
        interpretation.get(
            "comparison_scope",
            "none",
        )
    ).lower()

    if (
        comparison_scope == "local"
        and not valid_reference
        and not valid_context
        and not any(
            item.get("role") == "entity_identifier"
            for item in valid_detection
        )
    ):

        warnings.append(
            "The objective implies local comparison, "
            "but no meaningful grouping, reference or "
            "context column was confidently identified."
        )

    # --------------------------------------------------------
    # PHASE 3 AVAILABILITY
    # --------------------------------------------------------

    if not phase3_statistics:

        assumptions.append(
            "Phase 3 statistical evidence was not available "
            "during objective validation."
        )

    # --------------------------------------------------------
    # MISSING ATTRIBUTE WARNING
    # --------------------------------------------------------

    if missing_attributes:

        warnings.append(
            "One or more attributes required by the "
            "investigation objective were not included "
            "in the confirmed Phase 2 selection."
        )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        **interpretation,

        "attributes_involved":
            objective_attributes,

        "target_columns":
            valid_target,

        "reference_columns":
            valid_reference,

        "context_columns":
            valid_context,

        "attribute_selection_valid":
            selection_valid,

        "missing_attributes":
            missing_attributes,

        "assumptions":
            list(
                dict.fromkeys(
                    assumptions
                )
            ),

        "warnings":
            list(
                dict.fromkeys(
                    warnings
                )
            ),
    }


# ============================================================
# PHASE 5 HELPER
# ============================================================

def objective_feature_summary(
    interpretation: dict[str, Any],
) -> dict[str, Any]:

    detection_columns = interpretation.get(
        "target_columns",
        [],
    )

    reference_columns = interpretation.get(
        "reference_columns",
        [],
    )

    context_columns = interpretation.get(
        "context_columns",
        [],
    )

    return {
        "anomaly_type":
            interpretation.get(
                "anomaly_type",
                "point",
            ),

        "comparison_scope":
            interpretation.get(
                "comparison_scope",
                "none",
            ),

        "detection_behavior":
            interpretation.get(
                "detection_behavior",
                "",
            ),

        "temporal_requirement":
            interpretation.get(
                "temporal_requirement",
                "unclear",
            ),

        "detection_count":
            len(detection_columns),

        "target_count":
            len(detection_columns),

        "reference_count":
            len(reference_columns),

        "context_count":
            len(context_columns),

        "detection_columns": [
            item["column"]
            for item in detection_columns
            if item.get("column")
        ],

        "target_columns": [
            item["column"]
            for item in detection_columns
            if item.get("column")
        ],

        "reference_columns": [
            item["column"]
            for item in reference_columns
            if item.get("column")
        ],

        "context_columns": [
            item["column"]
            for item in context_columns
            if item.get("column")
        ],

        "detection_column_roles": [
            {
                "column": item.get("column"),
                "role": item.get("role"),
                "confidence": item.get("confidence"),
                "evidence": item.get("evidence"),
            }
            for item in detection_columns
            if item.get("column")
        ],

        "attribute_selection_valid":
            interpretation.get(
                "attribute_selection_valid",
                True,
            ),

        "missing_attributes":
            interpretation.get(
                "missing_attributes",
                [],
            ),
    }