from __future__ import annotations

from typing import Any

from app.models.model_catalog import get_model_catalog

STATISTICAL_CHARACTERISTICS = [
    "Dataset Size & Dimensionality",
    "Data Type & Feature Composition",
    "Distribution Analysis",
    "Extreme Value Analysis",
    "Feature Scale Analysis",
    "Correlation Analysis",
    "Cluster Structure Analysis",
    "Local Density & Neighborhood Analysis",
    "Temporal Structure Analysis",
    "Time-Series Pattern Analysis",
]


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _section(statistics: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = statistics.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _value(section: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in section:
            return section[key]
    return default


def _model_name(model: dict[str, Any]) -> str:
    return str(model.get("name") or model.get("display_name") or "").strip()


def _model_key(model: dict[str, Any]) -> str:
    name = _text(_model_name(model))

    if "isolation" in name or "iforest" in name:
        return "iforest"
    if name == "ecod" or "empirical cumulative" in name:
        return "ecod"
    if name == "copod" or "copula" in name:
        return "copod"
    if name == "knn" or "k-nearest" in name or "nearest neighbor" in name:
        return "knn"
    if name == "lof" or "local outlier" in name:
        return "lof"
    if name == "cblof" or "cluster-based" in name:
        return "cblof"
    if name == "hbos" or "histogram-based" in name:
        return "hbos"
    if "matrixprofile" in name or "matrix profile" in name:
        return "matrixprofile"
    if "spectralresidual" in name or "spectral residual" in name:
        return "spectralresidual"
    if "kshape" in name or "k-shape" in name:
        return "kshape"

    return name


def _is_time_series(model: dict[str, Any]) -> bool:
    return _text(model.get("category")) == "time series"


def _clip(value: float) -> float:
    return round(max(0.0, min(7.0, value)), 2)


def _dataset_evidence(statistics: dict[str, Any]) -> tuple[float, str]:
    s = _section(statistics, "dataset_overview", "dataset_size", "size_dimensionality")

    rows = _number(_value(s, "records", "rows", "n_rows", "row_count"))
    features = _number(_value(s, "features", "columns", "n_features", "column_count"))

    if rows <= 0:
        rows = _number(statistics.get("rows"))
    if features <= 0:
        features = _number(statistics.get("columns"))

    if rows <= 0 and features <= 0:
        return 3.5, "Dataset size information was not available."

    if rows >= 1000:
        row_score = 3.0
    elif rows >= 200:
        row_score = 2.7
    elif rows >= 50:
        row_score = 2.3
    else:
        row_score = 1.8

    if features <= 10:
        feature_score = 2.0
    elif features <= 50:
        feature_score = 1.7
    elif features <= 200:
        feature_score = 1.3
    else:
        feature_score = 1.0

    score = row_score + feature_score
    if 0 < features <= rows:
        score += 1.0

    return _clip(score), f"Records={rows:g}; features={features:g}."


def _composition_evidence(statistics: dict[str, Any]) -> tuple[float, str]:
    s = _section(
        statistics,
        "feature_composition",
        "data_type_feature_composition",
        "data_types",
    )

    numeric = _number(_value(s, "numerical", "numeric", "numeric_count", "numerical_count"))
    categorical = _number(_value(s, "categorical", "categorical_count"))
    temporal = _number(_value(s, "date_time", "datetime", "temporal", "datetime_count", "date_time_count"))

    if numeric <= 0 and categorical <= 0 and temporal <= 0:
        return 3.5, "Feature-type composition was not available."

    total = numeric + categorical + temporal
    score = 0.0

    if numeric > 0:
        score += 3.0
    if total > 0 and numeric / total >= 0.5:
        score += 2.0
    elif numeric > 0:
        score += 1.0
    if categorical > 0:
        score += 0.75
    if temporal > 0:
        score += 0.75

    return _clip(score), (
        f"Numerical={numeric:g}; categorical={categorical:g}; "
        f"date/time={temporal:g}."
    )


def _distribution_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(
        statistics,
        "distribution_statistics",
        "distribution_analysis",
        "distribution",
    )

    avg = _number(
        _value(s, "average_abs_skew", "mean_abs_skew", "avg_abs_skew"),
        default=-1.0,
    )
    maximum = _number(
        _value(s, "max_abs_skew", "maximum_abs_skew"),
        default=-1.0,
    )

    if avg < 0:
        features = _value(s, "features", "numeric_features", "statistics")
        skews = []
        if isinstance(features, list):
            for item in features:
                if isinstance(item, dict):
                    v = _value(item, "skew", "skewness")
                    if v is not None:
                        skews.append(abs(_number(v)))
        if skews:
            avg = sum(skews) / len(skews)
            maximum = max(skews)

    if avg < 0:
        return 3.5, 0.0, "Distribution statistics were not available."

    if maximum < 0:
        maximum = avg

    if avg <= 0.25:
        score = 5.5
    elif avg <= 0.75:
        score = 5.0
    elif avg <= 1.5:
        score = 4.2
    elif avg <= 3.0:
        score = 3.4
    else:
        score = 2.6

    return _clip(score), avg, (
        f"Average absolute skew={avg:.4f}; maximum absolute skew={maximum:.4f}."
    )


def _extreme_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(
        statistics,
        "iqr_analysis",
        "extreme_value_analysis",
        "extreme_values",
    )

    count = _number(
        _value(
            s,
            "extreme_observations",
            "extreme_count",
            "outlier_count",
            "total_extreme",
        ),
        default=-1.0,
    )

    if count < 0:
        nested = _section(s, "summary", "overall")
        count = _number(
            _value(nested, "extreme_observations", "extreme_count", "outlier_count"),
            default=-1.0,
        )

    if count < 0:
        return 3.5, 0.0, "Extreme-value statistics were not available."

    if count == 0:
        score = 4.0
    elif count <= 5:
        score = 5.5
    elif count <= 20:
        score = 6.5
    else:
        score = 7.0

    return _clip(score), count, f"Extreme observations={count:g}."


def _scale_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(statistics, "scale_summary", "feature_scale", "scale_analysis")

    ratio = _number(
        _value(s, "range_ratio", "scale_ratio", "max_range_ratio", "range_ratio_max"),
        default=-1.0,
    )

    if ratio < 0:
        ranges = _value(s, "ranges", "feature_ranges")
        values = []

        if isinstance(ranges, dict):
            for value in ranges.values():
                v = _number(value, default=-1.0)
                if v > 0:
                    values.append(v)
        elif isinstance(ranges, list):
            for item in ranges:
                if isinstance(item, dict):
                    v = _number(_value(item, "range", "value"), default=-1.0)
                    if v > 0:
                        values.append(v)

        if values:
            ratio = max(values) / max(min(values), 1e-12)

    if ratio < 0:
        return 3.5, 0.0, "Feature-scale statistics were not available."

    if ratio <= 2:
        score = 6.5
    elif ratio <= 10:
        score = 6.0
    elif ratio <= 100:
        score = 5.0
    elif ratio <= 1000:
        score = 4.0
    else:
        score = 3.0

    return _clip(score), ratio, f"Maximum-to-minimum feature range ratio={ratio:.4f}."


def _correlation_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(statistics, "correlation_analysis", "correlation")

    strongest = _number(
        _value(
            s,
            "strongest_correlation",
            "max_abs_correlation",
            "maximum_absolute_correlation",
        ),
        default=-1.0,
    )

    if strongest < 0:
        pairs = _value(s, "pairs", "correlations")
        values = []
        if isinstance(pairs, list):
            for item in pairs:
                if isinstance(item, dict):
                    v = _value(item, "correlation", "coefficient", "abs_correlation")
                    if v is not None:
                        values.append(abs(_number(v)))
        if values:
            strongest = max(values)

    if strongest < 0:
        return 3.5, 0.0, "Correlation statistics were not available."

    if strongest >= 0.9:
        score = 6.5
    elif strongest >= 0.7:
        score = 6.0
    elif strongest >= 0.4:
        score = 5.2
    elif strongest >= 0.2:
        score = 4.3
    else:
        score = 3.5

    return _clip(score), strongest, f"Strongest absolute correlation={strongest:.4f}."


def _cluster_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(statistics, "cluster_analysis", "cluster_structure", "clustering")

    silhouette = _number(
        _value(s, "silhouette_score", "silhouette", "best_silhouette"),
        default=-1.0,
    )
    clusters = _number(
        _value(s, "estimated_clusters", "n_clusters", "best_k", "clusters")
    )

    if silhouette < 0:
        return 3.5, 0.0, "Cluster-structure statistics were not available."

    if silhouette >= 0.7:
        score = 7.0
    elif silhouette >= 0.5:
        score = 6.5
    elif silhouette >= 0.25:
        score = 5.5
    else:
        score = 4.0

    return _clip(score), silhouette, (
        f"Silhouette={silhouette:.4f}; estimated clusters={clusters:g}."
    )


def _density_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(
        statistics,
        "density_analysis",
        "local_density",
        "neighborhood_analysis",
    )

    cv = _number(
        _value(
            s,
            "density_cv",
            "coefficient_of_variation",
            "cv",
            "density_variability",
        ),
        default=-1.0,
    )

    nn = _number(
        _value(
            s,
            "nearest_neighbor_mean_distance",
            "mean_nearest_neighbor_distance",
            "mean_nn_distance",
            "nn_mean_distance",
        ),
        default=-1.0,
    )

    if cv < 0:
        return 3.5, 0.0, "Local-density statistics were not available."

    if cv >= 0.75:
        score = 7.0
    elif cv >= 0.5:
        score = 6.5
    elif cv >= 0.25:
        score = 5.5
    elif cv > 0:
        score = 4.5
    else:
        score = 3.5

    extra = f"; mean nearest-neighbor distance={nn:.4f}" if nn >= 0 else ""
    return _clip(score), cv, f"Density coefficient of variation={cv:.4f}{extra}."


def _temporal_evidence(statistics: dict[str, Any]) -> tuple[float, bool, str]:
    s = _section(
        statistics,
        "temporal_structure",
        "temporal_analysis",
        "time_structure",
    )

    valid = _number(
        _value(s, "valid_timestamps", "valid_dates", "valid_timestamp_count")
    )
    chronological = _value(
        s,
        "chronological",
        "is_chronological",
        "ordered",
        default=None,
    )
    regular = _value(
        s,
        "regular_intervals",
        "regular",
        "is_regular",
        default=None,
    )

    present = valid > 0 or chronological is not None

    if not present:
        return 1.5, False, "Temporal structure was not detected."

    score = 4.0
    if valid > 0:
        score += 1.0
    if chronological is True or _text(chronological) in {"true", "yes"}:
        score += 0.75
    if regular is True or _text(regular) in {"true", "yes"}:
        score += 0.75

    return _clip(score), True, (
        f"Valid timestamps={valid:g}; chronological={chronological}; regular intervals={regular}."
    )


def _timeseries_evidence(statistics: dict[str, Any]) -> tuple[float, float, str]:
    s = _section(
        statistics,
        "time_series_summary",
        "time_series_analysis",
        "timeseries_summary",
    )

    autocorrelation = _number(
        _value(
            s,
            "strongest_lag_autocorrelation",
            "lag1_autocorrelation",
            "lag_1_autocorrelation",
            "autocorrelation",
        ),
        default=-1.0,
    )

    if autocorrelation < 0:
        return 1.5, 0.0, "Time-series pattern statistics were not available."

    magnitude = abs(autocorrelation)

    if magnitude >= 0.8:
        score = 7.0
    elif magnitude >= 0.6:
        score = 6.5
    elif magnitude >= 0.4:
        score = 5.5
    elif magnitude >= 0.2:
        score = 4.5
    else:
        score = 3.0

    return _clip(score), magnitude, (
        f"Strongest lag autocorrelation={autocorrelation:.4f}."
    )


def _model_adjustment(
    characteristic: str,
    model_key: str,
    base: float,
    *,
    density_cv: float,
    strongest_corr: float,
    silhouette: float,
    temporal_present: bool,
    temporal_pattern: float,
    extreme_count: float,
    scale_ratio: float,
    average_abs_skew: float,
) -> float:
    score = base

    if characteristic == "Dataset Size & Dimensionality":
        if model_key in {"iforest", "ecod", "copod", "hbos"}:
            score += 0.5
        elif model_key == "cblof":
            score += 0.3
        else:
            score += 0.2

    elif characteristic == "Data Type & Feature Composition":
        if model_key in {
            "ecod", "iforest", "copod", "knn",
            "lof", "cblof", "hbos"
        }:
            score += 0.6
        else:
            score += 0.2

    elif characteristic == "Distribution Analysis":
        if model_key in {"ecod", "copod", "hbos"}:
            score += 0.9 if average_abs_skew >= 0.75 else 0.5
        elif model_key in {"iforest", "knn", "lof", "cblof"}:
            score += 0.5
        else:
            score += 0.2

    elif characteristic == "Extreme Value Analysis":
        if model_key in {"ecod", "copod", "hbos"}:
            score += 1.0 if extreme_count > 0 else 0.3
        elif model_key == "iforest":
            score += 0.8 if extreme_count > 0 else 0.4
        elif model_key in {"knn", "lof"}:
            score += 0.5 if extreme_count > 0 else 0.3
        else:
            score += 0.3

    elif characteristic == "Feature Scale Analysis":
        if model_key in {"knn", "lof"}:
            score += 0.9 if scale_ratio <= 10 else 0.2
        elif model_key == "cblof":
            score += 0.7 if scale_ratio <= 10 else 0.2
        elif model_key in {"ecod", "copod", "hbos"}:
            score += 0.5
        else:
            score += 0.4

    elif characteristic == "Correlation Analysis":
        if model_key in {"iforest", "knn", "lof", "cblof"}:
            score += 0.7 if strongest_corr >= 0.7 else 0.4
        elif model_key in {"ecod", "copod", "hbos"}:
            score += 0.5
        else:
            score += 0.2

    elif characteristic == "Cluster Structure Analysis":
        if model_key == "cblof":
            score += 1.4 if silhouette >= 0.5 else 0.7
        elif model_key in {"knn", "lof"}:
            score += 0.7 if silhouette >= 0.5 else 0.3
        elif model_key == "iforest":
            score += 0.6
        else:
            score += 0.3

    elif characteristic == "Local Density & Neighborhood Analysis":
        if model_key == "lof":
            score += 1.8 if density_cv >= 0.5 else 0.8
        elif model_key == "knn":
            score += 1.5 if density_cv >= 0.5 else 0.7
        elif model_key == "cblof":
            score += 0.8
        elif model_key == "iforest":
            score += 0.5
        else:
            score += 0.3 if model_key in {"ecod", "copod", "hbos"} else 0.1

    elif characteristic == "Temporal Structure Analysis":
        # A timestamp used as contextual information must not automatically
        # make a time-series detector preferable.
        if model_key in {"matrixprofile", "spectralresidual", "kshape"}:
            score += 2.0 if temporal_present else 0.0
        else:
            score += 0.4 if temporal_present else 0.2

    elif characteristic == "Time-Series Pattern Analysis":
        if model_key == "matrixprofile":
            score += 2.5 if temporal_pattern >= 0.6 else 1.0
        elif model_key == "spectralresidual":
            score += 2.2 if temporal_pattern >= 0.4 else 0.8
        elif model_key == "kshape":
            score += 2.4 if temporal_pattern >= 0.4 else 0.8
        else:
            score += 0.2

    return _clip(score)


def score_statistical_suitability(
    phase3_statistics: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """
    Statistical Suitability = 70 points.

    Exactly ten Phase 3 characteristics are evaluated, each out of 7.
    Objective information from Phase 4 is intentionally not used here.
    """

    statistics = phase3_statistics if isinstance(phase3_statistics, dict) else {}

    dataset_score, dataset_evidence = _dataset_evidence(statistics)
    composition_score, composition_evidence = _composition_evidence(statistics)
    distribution_score, average_abs_skew, distribution_evidence = _distribution_evidence(statistics)
    extreme_score, extreme_count, extreme_evidence = _extreme_evidence(statistics)
    scale_score, scale_ratio, scale_evidence = _scale_evidence(statistics)
    correlation_score, strongest_corr, correlation_evidence = _correlation_evidence(statistics)
    cluster_score, silhouette, cluster_evidence = _cluster_evidence(statistics)
    density_score, density_cv, density_evidence = _density_evidence(statistics)
    temporal_score, temporal_present, temporal_evidence = _temporal_evidence(statistics)
    timeseries_score, temporal_pattern, timeseries_evidence = _timeseries_evidence(statistics)

    bases = {
        "Dataset Size & Dimensionality": dataset_score,
        "Data Type & Feature Composition": composition_score,
        "Distribution Analysis": distribution_score,
        "Extreme Value Analysis": extreme_score,
        "Feature Scale Analysis": scale_score,
        "Correlation Analysis": correlation_score,
        "Cluster Structure Analysis": cluster_score,
        "Local Density & Neighborhood Analysis": density_score,
        "Temporal Structure Analysis": temporal_score,
        "Time-Series Pattern Analysis": timeseries_score,
    }

    evidence = {
        "Dataset Size & Dimensionality": dataset_evidence,
        "Data Type & Feature Composition": composition_evidence,
        "Distribution Analysis": distribution_evidence,
        "Extreme Value Analysis": extreme_evidence,
        "Feature Scale Analysis": scale_evidence,
        "Correlation Analysis": correlation_evidence,
        "Cluster Structure Analysis": cluster_evidence,
        "Local Density & Neighborhood Analysis": density_evidence,
        "Temporal Structure Analysis": temporal_evidence,
        "Time-Series Pattern Analysis": timeseries_evidence,
    }

    results: dict[str, dict[str, Any]] = {}

    for model in get_model_catalog():
        model_name = _model_name(model)
        model_key = _model_key(model)
        details = []

        for characteristic in STATISTICAL_CHARACTERISTICS:
            score = _model_adjustment(
                characteristic,
                model_key,
                bases[characteristic],
                density_cv=density_cv,
                strongest_corr=strongest_corr,
                silhouette=silhouette,
                temporal_present=temporal_present,
                temporal_pattern=temporal_pattern,
                extreme_count=extreme_count,
                scale_ratio=scale_ratio,
                average_abs_skew=average_abs_skew,
            )

            details.append({
                "factor": characteristic,
                "name": characteristic,
                "score": score,
                "maximum": 7.0,
                "max_score": 7.0,
            })

        total = round(
            min(70.0, sum(float(item["score"]) for item in details)),
            2,
        )

        results[model_name] = {
            "score": total,
            "maximum": 70.0,
            "max_score": 70.0,
            "details": details,
        }

    return results
