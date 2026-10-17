from __future__ import annotations

from typing import Any

from app.models.model_catalog import get_model_catalog


def _text(value: Any) -> str:
    return str(
        value or ""
    ).strip().lower()


def _anomaly_type(
    objective: dict[str, Any],
) -> str:

    return _text(
        objective.get("anomaly_type")
        or objective.get("type")
    )


def _temporal_required(
    objective: dict[str, Any],
) -> bool:

    value = _text(
        objective.get(
            "temporal_requirement"
        )
    )

    return value in {
        "required",
        "yes",
        "true",
        "strongly_required",
    }


def _detection_count(
    objective: dict[str, Any],
) -> int:

    for key in (
        "target_columns",
        "detection_columns",
    ):

        items = objective.get(key)

        if isinstance(items, list):
            return len(items)

    return 0


def _role_bonus(
    objective: dict[str, Any],
    model: dict,
) -> float:
    """
    Relevant Feature Compatibility /5.

    Uses semantic roles supplied by Phase 4.
    """

    roles = set()

    for key in (
        "target_columns",
        "reference_columns",
        "context_columns",
    ):

        items = objective.get(
            key,
            [],
        )

        if not isinstance(
            items,
            list,
        ):
            continue

        for item in items:

            if not isinstance(
                item,
                dict,
            ):
                continue

            role = _text(
                item.get("role")
            )

            if role:
                roles.add(role)

    category = _text(
        model.get("category")
    )

    if category == "time series":

        if (
            "temporal_feature"
            in roles
        ):
            return 5.0

        return 2.0

    if roles & {
        "detection_feature",
        "context_feature",
        "reference_feature",
        "entity_identifier",
    }:
        return 4.0

    return 2.5


def _anomaly_compatibility(
    objective: dict[str, Any],
    model: dict,
) -> float:

    anomaly_type = _anomaly_type(
        objective
    )

    category = _text(
        model.get("category")
    )

    if category == "time series":

        if anomaly_type in {
            "temporal",
            "contextual",
            "collective",
            "sequential",
            "time_series",
            "time-series",
        }:
            return 15.0

        if _temporal_required(
            objective
        ):
            return 13.0

        return 6.0

    if anomaly_type in {
        "point",
        "point_anomaly",
        "point anomaly",
        "global",
        "global_anomaly",
    }:
        return 13.0

    if anomaly_type in {
        "contextual",
        "contextual_anomaly",
        "contextual anomaly",
    }:
        return 12.0

    if anomaly_type in {
        "collective",
        "collective_anomaly",
        "collective anomaly",
    }:
        return 8.0

    return 9.0


def _semantic_compatibility(
    objective: dict[str, Any],
    model: dict,
) -> float:

    behavior = _text(
        objective.get(
            "detection_behavior"
        )
        or objective.get(
            "detection_behavior_reason"
        )
    )

    scope = _text(
        objective.get(
            "comparison_scope"
        )
    )

    category = _text(
        model.get("category")
    )

    if category == "time series":

        if (
            _temporal_required(
                objective
            )
            or "temporal" in behavior
            or "sequential" in behavior
            or scope in {
                "temporal",
                "time",
                "local_temporal",
            }
        ):
            return 9.0

        return 3.5

    if scope in {
        "local",
        "group",
        "entity",
        "contextual",
        "conditional",
    }:
        return 9.0

    if behavior:
        return 8.0

    return 6.5


def score_objective_suitability(
    objective: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Objective Compatibility:

        Anomaly Type Compatibility = 15
        Semantic Objective Compatibility = 10
        Relevant Feature Compatibility = 5

        Total = 30
    """

    results: dict[
        str,
        dict[str, Any],
    ] = {}

    for model in get_model_catalog():

        anomaly_score = (
            _anomaly_compatibility(
                objective,
                model,
            )
        )

        semantic_score = (
            _semantic_compatibility(
                objective,
                model,
            )
        )

        feature_score = (
            _role_bonus(
                objective,
                model,
            )
        )

        details = [

            {
                "factor":
                    "Anomaly Type Compatibility",

                "name":
                    "Anomaly Type Compatibility",

                "score":
                    round(
                        anomaly_score,
                        2,
                    ),

                "maximum":
                    15.0,

                "max_score":
                    15.0,
            },

            {
                "factor":
                    "Semantic Objective Compatibility",

                "name":
                    "Semantic Objective Compatibility",

                "score":
                    round(
                        semantic_score,
                        2,
                    ),

                "maximum":
                    10.0,

                "max_score":
                    10.0,
            },

            {
                "factor":
                    "Relevant Feature Compatibility",

                "name":
                    "Relevant Feature Compatibility",

                "score":
                    round(
                        feature_score,
                        2,
                    ),

                "maximum":
                    5.0,

                "max_score":
                    5.0,
            },
        ]

        total = (
            anomaly_score
            + semantic_score
            + feature_score
        )

        results[
            model["name"]
        ] = {
            "score":
                round(
                    min(
                        30.0,
                        total,
                    ),
                    2,
                ),

            "maximum":
                30.0,

            "details":
                details,
        }

    return results