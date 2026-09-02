from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------
# MODEL CAPABILITIES
# ---------------------------------------------------------------------
# These are model capability descriptions, not dataset-specific rules.
# They allow the recommendation engine to compare the current evidence
# against known detector characteristics.
# ---------------------------------------------------------------------

MODEL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "ECOD": {
        "family": "distribution",
        "strengths": {
            "point": 1.0,
            "contextual": 0.45,
            "collective": 0.25,
        },
        "scopes": {
            "global": 1.0,
            "local": 0.45,
            "temporal": 0.25,
            "none": 1.0,
        },
        "behaviors": {
            "unusual_values": 1.0,
            "distribution_deviation": 1.0,
            "record_deviation": 0.9,
            "group_pattern": 0.3,
            "sequence_pattern": 0.2,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.7,
            "high_dimensional": 0.7,
        },
        "distribution": {
            "symmetric": 0.75,
            "moderate_skew": 0.95,
            "high_skew": 1.0,
        },
        "scale_sensitive": False,
        "cluster_sensitive": False,
        "temporal_native": False,
    },

    "COPOD": {
        "family": "distribution",
        "strengths": {
            "point": 1.0,
            "contextual": 0.45,
            "collective": 0.25,
        },
        "scopes": {
            "global": 1.0,
            "local": 0.45,
            "temporal": 0.25,
            "none": 1.0,
        },
        "behaviors": {
            "unusual_values": 1.0,
            "distribution_deviation": 1.0,
            "record_deviation": 0.9,
            "group_pattern": 0.3,
            "sequence_pattern": 0.2,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.7,
            "high_dimensional": 0.75,
        },
        "distribution": {
            "symmetric": 0.8,
            "moderate_skew": 1.0,
            "high_skew": 1.0,
        },
        "scale_sensitive": False,
        "cluster_sensitive": False,
        "temporal_native": False,
    },

    "HBOS": {
        "family": "histogram",
        "strengths": {
            "point": 0.95,
            "contextual": 0.35,
            "collective": 0.2,
        },
        "scopes": {
            "global": 1.0,
            "local": 0.35,
            "temporal": 0.2,
            "none": 1.0,
        },
        "behaviors": {
            "unusual_values": 1.0,
            "distribution_deviation": 0.95,
            "record_deviation": 0.85,
            "group_pattern": 0.25,
            "sequence_pattern": 0.15,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.6,
            "high_dimensional": 0.6,
        },
        "distribution": {
            "symmetric": 0.85,
            "moderate_skew": 0.95,
            "high_skew": 0.9,
        },
        "scale_sensitive": False,
        "cluster_sensitive": False,
        "temporal_native": False,
    },

    "Isolation Forest": {
        "family": "isolation",
        "strengths": {
            "point": 1.0,
            "contextual": 0.65,
            "collective": 0.55,
        },
        "scopes": {
            "global": 1.0,
            "local": 0.7,
            "temporal": 0.4,
            "none": 1.0,
        },
        "behaviors": {
            "unusual_values": 0.9,
            "distribution_deviation": 0.85,
            "record_deviation": 1.0,
            "group_pattern": 0.6,
            "sequence_pattern": 0.4,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.75,
            "high_dimensional": 1.0,
        },
        "distribution": {
            "symmetric": 0.9,
            "moderate_skew": 0.9,
            "high_skew": 0.9,
        },
        "scale_sensitive": False,
        "cluster_sensitive": True,
        "temporal_native": False,
    },

    "KNN": {
        "family": "distance",
        "strengths": {
            "point": 0.95,
            "contextual": 0.7,
            "collective": 0.5,
        },
        "scopes": {
            "global": 0.9,
            "local": 0.8,
            "temporal": 0.4,
            "none": 0.9,
        },
        "behaviors": {
            "unusual_values": 0.8,
            "distribution_deviation": 0.7,
            "record_deviation": 1.0,
            "group_pattern": 0.7,
            "sequence_pattern": 0.35,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.65,
            "high_dimensional": 0.45,
        },
        "distribution": {
            "symmetric": 0.85,
            "moderate_skew": 0.8,
            "high_skew": 0.75,
        },
        "scale_sensitive": True,
        "cluster_sensitive": True,
        "temporal_native": False,
    },

    "LOF": {
        "family": "density",
        "strengths": {
            "point": 0.9,
            "contextual": 0.85,
            "collective": 0.55,
        },
        "scopes": {
            "global": 0.75,
            "local": 0.95,
            "temporal": 0.4,
            "none": 0.8,
        },
        "behaviors": {
            "unusual_values": 0.75,
            "distribution_deviation": 0.65,
            "record_deviation": 0.95,
            "group_pattern": 0.85,
            "sequence_pattern": 0.35,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.6,
            "high_dimensional": 0.4,
        },
        "distribution": {
            "symmetric": 0.8,
            "moderate_skew": 0.75,
            "high_skew": 0.7,
        },
        "scale_sensitive": True,
        "cluster_sensitive": True,
        "temporal_native": False,
    },

    "CBLOF": {
        "family": "cluster",
        "strengths": {
            "point": 0.8,
            "contextual": 0.75,
            "collective": 0.8,
        },
        "scopes": {
            "global": 0.7,
            "local": 0.85,
            "temporal": 0.35,
            "none": 0.75,
        },
        "behaviors": {
            "unusual_values": 0.65,
            "distribution_deviation": 0.55,
            "record_deviation": 0.85,
            "group_pattern": 1.0,
            "sequence_pattern": 0.3,
        },
        "data": {
            "numeric": 1.0,
            "mixed": 0.55,
            "high_dimensional": 0.5,
        },
        "distribution": {
            "symmetric": 0.75,
            "moderate_skew": 0.75,
            "high_skew": 0.7,
        },
        "scale_sensitive": True,
        "cluster_sensitive": True,
        "temporal_native": False,
    },
}


# ---------------------------------------------------------------------
# STATISTICAL FACTORS
# ---------------------------------------------------------------------
# Your original requirement lists 75 raw points.
# We retain every factor and normalize raw /75 -> statistical /70.
# ---------------------------------------------------------------------

STATISTICAL_WEIGHTS = {
    "Dataset Size": 5,
    "Number of Features": 5,
    "Dimensionality": 5,
    "Data Type": 5,
    "Distribution": 10,
    "Extreme Values": 5,
    "Sparsity": 5,
    "Correlation": 5,
    "Feature Scale": 5,
    "Missing Values": 5,
    "Duplicate Records": 5,
    "Cluster Structure": 5,
    "Temporal Structure": 5,
    "Data Density": 5,
}

STATISTICAL_RAW_MAXIMUM = sum(
    STATISTICAL_WEIGHTS.values()
)

STATISTICAL_MAXIMUM = 70.0


OBJECTIVE_WEIGHTS = {
    "Anomaly Type Match": 10,
    "Comparison Scope Match": 6,
    "Detection Behavior Match": 6,
    "Target Column Match": 4,
    "Reference/Context Column Match": 2,
    "Temporal Requirement Match": 2,
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(
    data: dict[str, Any],
    *keys: str,
    default: str = "",
) -> str:

    for key in keys:
        value = data.get(key)

        if value is not None:
            return str(value).lower()

    return default


def _normalised_match(
    value: str,
    mapping: dict[str, float],
) -> float:

    value = value.lower().strip()

    if value in mapping:
        return mapping[value]

    for key, score in mapping.items():
        if key in value:
            return score

    return 0.5


def _factor_score(
    factor: str,
    profile: dict[str, Any],
) -> tuple[float, str]:

    maximum = STATISTICAL_WEIGHTS[factor]

    if factor == "Dataset Size":
        value = _text(
            profile,
            "dataset_size",
            "size",
        )

        mapping = {
            "small": 1.0,
            "medium": 1.0,
            "large": 0.9,
            "very large": 0.85,
        }

        ratio = _normalised_match(value, mapping)

    elif factor == "Number of Features":
        count = _number(
            profile.get("number_of_features")
            or profile.get("features")
            or profile.get("column_count")
        )

        if count <= 0:
            ratio = 0.5
        elif count <= 50:
            ratio = 1.0
        elif count <= 200:
            ratio = 0.9
        else:
            ratio = 0.8

    elif factor == "Dimensionality":
        value = _text(
            profile,
            "dimensionality",
        )

        ratio = _normalised_match(
            value,
            {
                "low": 1.0,
                "medium": 0.95,
                "high": 0.85,
            },
        )

    elif factor == "Data Type":
        value = _text(
            profile,
            "data_type",
            "datatype",
        )

        ratio = _normalised_match(
            value,
            {
                "numeric": 1.0,
                "mixed": 0.8,
                "categorical": 0.55,
                "text": 0.5,
            },
        )

    elif factor == "Distribution":
        value = _text(
            profile,
            "distribution",
        )

        ratio = _normalised_match(
            value,
            {
                "symmetric": 0.8,
                "moderately skewed": 0.95,
                "moderate skew": 0.95,
                "highly skewed": 1.0,
                "high skew": 1.0,
            },
        )

    elif factor == "Extreme Values":
        value = _text(
            profile,
            "extreme_values",
            "extremes",
        )

        ratio = (
            1.0
            if value in {
                "present",
                "yes",
                "true",
                "high",
            }
            else 0.85
        )

    elif factor == "Sparsity":
        value = _text(
            profile,
            "sparsity",
        )

        ratio = _normalised_match(
            value,
            {
                "low": 1.0,
                "medium": 0.85,
                "high": 0.8,
            },
        )

    elif factor == "Correlation":
        value = _text(
            profile,
            "correlation",
        )

        ratio = _normalised_match(
            value,
            {
                "low": 0.85,
                "moderate": 0.9,
                "high": 0.95,
            },
        )

    elif factor == "Feature Scale":
        value = _text(
            profile,
            "feature_scale",
            "scale",
        )

        ratio = _normalised_match(
            value,
            {
                "same": 0.9,
                "similar": 0.9,
                "different": 0.95,
                "different scales": 0.95,
            },
        )

    elif factor == "Missing Values":
        value = _text(
            profile,
            "missing_values",
            "missing",
        )

        ratio = (
            0.95
            if value in {
                "none",
                "no",
                "false",
            }
            else 0.8
        )

    elif factor == "Duplicate Records":
        value = _text(
            profile,
            "duplicate_records",
            "duplicates",
        )

        ratio = (
            0.95
            if value in {
                "none",
                "no",
                "false",
            }
            else 0.8
        )

    elif factor == "Cluster Structure":
        value = _text(
            profile,
            "cluster_structure",
            "clusters",
        )

        ratio = _normalised_match(
            value,
            {
                "present": 1.0,
                "clusters present": 1.0,
                "weak": 0.8,
                "absent": 0.8,
                "none": 0.8,
            },
        )

    elif factor == "Temporal Structure":
        value = _text(
            profile,
            "temporal_structure",
            "temporal",
        )

        ratio = _normalised_match(
            value,
            {
                "present": 1.0,
                "present": 1.0,
                "absent": 0.8,
                "none": 0.8,
            },
        )

    elif factor == "Data Density":
        value = _text(
            profile,
            "data_density",
            "density",
        )

        ratio = _normalised_match(
            value,
            {
                "dense": 0.95,
                "medium": 0.9,
                "sparse": 0.85,
            },
        )

    else:
        ratio = 0.5

    ratio = max(0.0, min(1.0, ratio))
    score = maximum * ratio

    return score, (
        f"{factor} suitability was estimated from the "
        f"Phase 3 dataset evidence ({value if 'value' in locals() else ratio})."
    )


def calculate_statistical_score(
    *,
    statistical_profile: dict[str, Any],
    model_name: str,
) -> tuple[float, list[dict[str, Any]]]:

    details = []
    raw_total = 0.0

    capabilities = MODEL_CAPABILITIES[model_name]

    for factor, maximum in STATISTICAL_WEIGHTS.items():

        base_score, reason = _factor_score(
            factor,
            statistical_profile,
        )

        ratio = (
            base_score / maximum
            if maximum
            else 0.0
        )

        # Model-specific adjustments.
        if factor == "Distribution":
            distribution = _text(
                statistical_profile,
                "distribution",
            )

            ratio *= capabilities.get(
                "distribution",
                {},
            ).get(
                distribution,
                0.85,
            )

        elif factor == "Feature Scale":
            if capabilities.get(
                "scale_sensitive",
                False,
            ):
                ratio *= 0.8

        elif factor == "Cluster Structure":
            cluster_value = _text(
                statistical_profile,
                "cluster_structure",
                "clusters",
            )

            if (
                "present" in cluster_value
                and capabilities.get(
                    "cluster_sensitive",
                    False,
                )
            ):
                ratio = min(
                    1.0,
                    ratio * 1.1,
                )

        elif factor == "Temporal Structure":
            temporal_value = _text(
                statistical_profile,
                "temporal_structure",
                "temporal",
            )

            if (
                "present" in temporal_value
                and capabilities.get(
                    "temporal_native",
                    False,
                )
            ):
                ratio = min(
                    1.0,
                    ratio * 1.1,
                )

        ratio = max(0.0, min(1.0, ratio))

        score = maximum * ratio
        raw_total += score

        details.append(
            {
                "factor": factor,
                "score": round(score, 2),
                "maximum": maximum,
                "reason": reason,
            }
        )

    # Preserve all 14 factors while producing the required /70 score.
    normalized = (
        raw_total
        / STATISTICAL_RAW_MAXIMUM
        * STATISTICAL_MAXIMUM
    )

    return round(normalized, 2), details


def _behavior_category(
    interpretation: dict[str, Any],
) -> str:

    anomaly_type = interpretation.get(
        "anomaly_type",
        "point",
    )

    behavior = str(
        interpretation.get(
            "detection_behavior",
            "",
        )
    ).lower()

    if anomaly_type == "collective":
        if any(
            token in behavior
            for token in (
                "sequence",
                "pattern",
                "trend",
                "group",
                "series",
            )
        ):
            return "sequence_pattern"

        return "group_pattern"

    if any(
        token in behavior
        for token in (
            "distribution",
            "skew",
            "tail",
        )
    ):
        return "distribution_deviation"

    if any(
        token in behavior
        for token in (
            "value",
            "high",
            "low",
            "unusual",
        )
    ):
        return "unusual_values"

    return "record_deviation"


def calculate_objective_score(
    *,
    interpretation: dict[str, Any],
    column_profiles: dict[str, dict[str, Any]],
    model_name: str,
) -> tuple[float, list[dict[str, Any]]]:

    capabilities = MODEL_CAPABILITIES[model_name]

    details = []
    total = 0.0

    anomaly_type = interpretation.get(
        "anomaly_type",
        "point",
    )

    anomaly_ratio = capabilities.get(
        "strengths",
        {},
    ).get(
        anomaly_type,
        0.3,
    )

    score = (
        OBJECTIVE_WEIGHTS["Anomaly Type Match"]
        * anomaly_ratio
    )

    details.append(
        {
            "factor": "Anomaly Type Match",
            "score": round(score, 2),
            "maximum": 10,
            "reason": (
                f"{model_name} capability for "
                f"{anomaly_type} anomaly detection."
            ),
        }
    )

    total += score

    scope = interpretation.get(
        "comparison_scope",
        "none",
    )

    scope_ratio = capabilities.get(
        "scopes",
        {},
    ).get(
        scope,
        0.3,
    )

    score = (
        OBJECTIVE_WEIGHTS["Comparison Scope Match"]
        * scope_ratio
    )

    details.append(
        {
            "factor": "Comparison Scope Match",
            "score": round(score, 2),
            "maximum": 6,
            "reason": (
                f"The objective requires '{scope}' comparison."
            ),
        }
    )

    total += score

    behavior_category = _behavior_category(
        interpretation
    )

    behavior_ratio = capabilities.get(
        "behaviors",
        {},
    ).get(
        behavior_category,
        0.3,
    )

    score = (
        OBJECTIVE_WEIGHTS["Detection Behavior Match"]
        * behavior_ratio
    )

    details.append(
        {
            "factor": "Detection Behavior Match",
            "score": round(score, 2),
            "maximum": 6,
            "reason": (
                f"Detected objective behavior category: "
                f"{behavior_category}."
            ),
        }
    )

    total += score

    target_columns = interpretation.get(
        "target_columns",
        [],
    )

    target_ratio = 1.0 if target_columns else 0.25

    score = (
        OBJECTIVE_WEIGHTS["Target Column Match"]
        * target_ratio
    )

    details.append(
        {
            "factor": "Target Column Match",
            "score": round(score, 2),
            "maximum": 4,
            "reason": (
                "A target column was semantically mapped from "
                "the user's objective."
                if target_columns
                else
                "No confident target column was identified."
            ),
        }
    )

    total += score

    reference_columns = interpretation.get(
        "reference_columns",
        [],
    )

    context_columns = interpretation.get(
        "context_columns",
        [],
    )

    reference_ratio = (
        1.0
        if reference_columns or context_columns
        else 0.25
    )

    score = (
        OBJECTIVE_WEIGHTS[
            "Reference/Context Column Match"
        ]
        * reference_ratio
    )

    details.append(
        {
            "factor": "Reference/Context Column Match",
            "score": round(score, 2),
            "maximum": 2,
            "reason": (
                "Reference/context columns were identified."
                if reference_columns or context_columns
                else
                "No reference/context column was identified."
            ),
        }
    )

    total += score

    temporal_requirement = interpretation.get(
        "temporal_requirement",
        "unclear",
    )

    has_temporal_column = any(
        any(
            token in str(
                column_profiles.get(
                    column,
                    {},
                ).get(
                    "type",
                    "",
                )
            ).lower()
            for token in (
                "date",
                "time",
                "datetime",
                "timestamp",
            )
        )
        for column in column_profiles
    )

    if temporal_requirement == "not_required":
        temporal_ratio = 1.0
    elif temporal_requirement == "required":
        temporal_ratio = (
            1.0 if has_temporal_column else 0.25
        )
    else:
        temporal_ratio = 0.7

    score = (
        OBJECTIVE_WEIGHTS[
            "Temporal Requirement Match"
        ]
        * temporal_ratio
    )

    details.append(
        {
            "factor": "Temporal Requirement Match",
            "score": round(score, 2),
            "maximum": 2,
            "reason": (
                f"Temporal requirement: "
                f"{temporal_requirement}."
            ),
        }
    )

    total += score

    return round(total, 2), details


def _recommendation_reason(
    model_name: str,
    statistical_score: float,
    objective_score: float,
    interpretation: dict[str, Any],
) -> str:

    anomaly_type = interpretation.get(
        "anomaly_type",
        "point",
    )

    scope = interpretation.get(
        "comparison_scope",
        "none",
    )

    return (
        f"{model_name} is recommended because its detector "
        f"characteristics provide a statistical suitability score "
        f"of {statistical_score:.2f}/70 and an objective suitability "
        f"score of {objective_score:.2f}/30 for the interpreted "
        f"{anomaly_type} anomaly with {scope} comparison behavior."
    )


def recommend_models(
    *,
    statistical_profile: dict[str, Any],
    interpretation: dict[str, Any],
    column_profiles: dict[str, dict[str, Any]],
    top_n: int = 3,
) -> list[dict[str, Any]]:

    recommendations = []

    for model_name in MODEL_CAPABILITIES:

        statistical_score, statistical_details = (
            calculate_statistical_score(
                statistical_profile=statistical_profile,
                model_name=model_name,
            )
        )

        objective_score, objective_details = (
            calculate_objective_score(
                interpretation=interpretation,
                column_profiles=column_profiles,
                model_name=model_name,
            )
        )

        final_score = (
            statistical_score
            + objective_score
        )

        recommendations.append(
            {
                "model": model_name,
                "statistical_score": statistical_score,
                "statistical_maximum": 70.0,
                "objective_score": objective_score,
                "objective_maximum": 30.0,
                "final_score": round(
                    min(100.0, final_score),
                    2,
                ),
                "final_maximum": 100.0,
                "recommendation_reason": (
                    _recommendation_reason(
                        model_name,
                        statistical_score,
                        objective_score,
                        interpretation,
                    )
                ),
                "statistical_details": statistical_details,
                "objective_details": objective_details,
            }
        )

    recommendations.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    recommendations = recommendations[:top_n]

    for index, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        recommendation["rank"] = index

    return recommendations