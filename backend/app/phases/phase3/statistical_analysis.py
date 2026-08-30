from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


def _finite_float(value: Any, digits: int = 4) -> float | None:
    try:
        value = float(value)
        return round(value, digits) if math.isfinite(value) else None
    except Exception:
        return None


def _distribution_label(skew: float) -> str:
    a = abs(skew)
    return "Approximately Normal" if a <= 0.5 else "Moderately Skewed" if a <= 1 else "Highly Skewed"


def _relationship(r: float) -> str:
    a = abs(r)
    if a < 0.1: return "Very weak"
    if a < 0.3: return "Weak"
    if a < 0.7: return "Moderate"
    if a < 0.9: return "Strong"
    return "Very strong"


def _scale_label(ratio: float) -> str:
    if ratio <= 10: return "Similar"
    if ratio <= 100: return "Different"
    if ratio <= 1000: return "Very different"
    return "Highly Different"


def _cluster_analysis(X: np.ndarray) -> dict[str, Any]:
    n = len(X)
    if n < 4:
        return {"estimated_clusters": None, "silhouette_score": None,
                "cluster_structure": "Unavailable", "reason": "At least 4 records are required."}
    best_k, best_score = None, -1.0
    for k in range(2, min(8, n - 1) + 1):
        try:
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
            if len(set(labels)) < 2:
                continue
            score = float(silhouette_score(X, labels))
            if score > best_score:
                best_k, best_score = k, score
        except Exception:
            continue
    if best_k is None:
        return {"estimated_clusters": None, "silhouette_score": None,
                "cluster_structure": "Unavailable", "reason": "Cluster structure could not be estimated."}
    label = "Strong" if best_score >= 0.5 else "Moderate" if best_score >= 0.25 else "Weak"
    return {"estimated_clusters": int(best_k), "silhouette_score": round(best_score, 4),
            "cluster_structure": label, "reason": None}


def _density_analysis(X: np.ndarray) -> dict[str, Any]:
    n = len(X)
    if n < 3:
        return {"mean_nearest_neighbor_distance": None, "density_variability_cv": None,
                "local_density": "Unavailable"}
    model = NearestNeighbors(n_neighbors=min(2, n)).fit(X)
    distances, _ = model.kneighbors(X)
    nearest = distances[:, -1]
    mean_distance = float(np.mean(nearest))
    std_distance = float(np.std(nearest, ddof=1)) if n > 1 else 0.0
    cv = std_distance / mean_distance if mean_distance else 0.0
    return {"mean_nearest_neighbor_distance": round(mean_distance, 4),
            "density_variability_cv": round(cv, 4),
            "local_density": "Variable" if cv >= 0.3 else "Relatively uniform"}


def analyze_statistics(df: pd.DataFrame, selected_columns: list[str],
                       summary: dict[str, Any]) -> dict[str, Any]:
    numeric_columns = [c for c in summary.get("numeric_column_names", [])
                       if c in selected_columns and c in df.columns]
    datetime_columns = [c for c in summary.get("datetime_column_names", [])
                        if c in selected_columns and c in df.columns]
    categorical_columns = [c for c in selected_columns
                           if c not in numeric_columns and c not in datetime_columns]

    distributions, extreme_rows, scale_rows = [], [], []
    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            continue
        mean, median = float(values.mean()), float(values.median())
        std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        skew = float(values.skew()) if len(values) >= 3 else 0.0
        q1, q3 = float(values.quantile(.25)), float(values.quantile(.75))
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        extreme = int(((values < lower) | (values > upper)).sum())
        mn, mx = float(values.min()), float(values.max())
        distributions.append({
            "feature": column, "mean": _finite_float(mean), "median": _finite_float(median),
            "std": _finite_float(std), "skewness": _finite_float(skew),
            "distribution": _distribution_label(skew),
        })
        extreme_rows.append({
            "feature": column, "q1": _finite_float(q1), "q3": _finite_float(q3),
            "lower_bound": _finite_float(lower), "upper_bound": _finite_float(upper),
            "extreme_values": extreme, "extreme_percentage": round(extreme / len(values) * 100, 4),
        })
        scale_rows.append({
            "feature": column, "minimum": _finite_float(mn), "maximum": _finite_float(mx),
            "range": _finite_float(mx - mn),
        })

    correlation_rows = []
    if len(numeric_columns) >= 2:
        corr = df[numeric_columns].apply(pd.to_numeric, errors="coerce").corr(method="pearson")
        for i, a in enumerate(numeric_columns):
            for b in numeric_columns[i + 1:]:
                value = corr.loc[a, b]
                if pd.notna(value):
                    correlation_rows.append({
                        "feature_a": a, "feature_b": b, "correlation": round(float(value), 4),
                        "relationship": _relationship(float(value)),
                    })

    ranges = [float(r["range"]) for r in scale_rows if r["range"] is not None and r["range"] > 0]
    scale_ratio = max(ranges) / min(ranges) if ranges else 0.0
    scale_classification = _scale_label(scale_ratio) if ranges else "Unavailable"

    cluster_result = {"estimated_clusters": None, "silhouette_score": None,
                      "cluster_structure": "Unavailable", "reason": "No suitable numerical matrix."}
    density_result = {"mean_nearest_neighbor_distance": None, "density_variability_cv": None,
                      "local_density": "Unavailable"}
    if numeric_columns and len(df) >= 4:
        matrix = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
        matrix = matrix.fillna(matrix.median(numeric_only=True)).dropna()
        if len(matrix) >= 4 and matrix.shape[1] >= 1:
            X = StandardScaler().fit_transform(matrix)
            cluster_result, density_result = _cluster_analysis(X), _density_analysis(X)

    temporal = {"temporal_column": datetime_columns[0] if datetime_columns else None,
                "valid_timestamps": 0, "chronological_ordering": "Not applicable",
                "interval": "—", "regular_intervals": False}
    if datetime_columns:
        dt = pd.to_datetime(df[datetime_columns[0]], errors="coerce", format="mixed").dropna()
        temporal["valid_timestamps"] = int(len(dt))
        if len(dt) >= 2:
            ordered = dt.sort_values()
            temporal["chronological_ordering"] = bool(ordered.is_monotonic_increasing)
            deltas = ordered.diff().dropna().dt.total_seconds()
            if not deltas.empty:
                med = float(deltas.median())
                temporal["interval"] = round(med / 86400, 6)
                temporal["regular_intervals"] = bool(np.allclose(deltas.values, med, rtol=.01, atol=1e-6))

    temporal_present = bool(datetime_columns and temporal["valid_timestamps"] > 0)
    row_count, feature_count = len(df), len(selected_columns)
    avg_per_numeric = row_count / len(numeric_columns) if numeric_columns else 0
    abs_skews = [abs(float(r["skewness"])) for r in distributions if r["skewness"] is not None]
    avg_abs_skew = float(np.mean(abs_skews)) if abs_skews else 0.0
    strongest_corr = max((abs(r["correlation"]) for r in correlation_rows), default=0.0)
    extreme_total = sum(r["extreme_values"] for r in extreme_rows)
    dataset_size = "Small" if row_count < 5000 else "Medium" if row_count < 100000 else "Large"
    dimensionality = "Low" if feature_count <= 10 else "Moderate" if feature_count <= 50 else "High"
    data_type = "Mixed" if numeric_columns and categorical_columns else "Numerical" if numeric_columns else "Categorical" if categorical_columns else "Other"

    sections = {
        "overview": {
            "title": "1. Dataset Size & Dimensionality", "result": dataset_size,
            "dataset_overview": {"records": row_count, "features": feature_count,
                                 "dataset_size": dataset_size, "dimensionality": dimensionality,
                                 "data_type": data_type},
            "inferences": [
                f"The processed dataset contains {row_count} records across {feature_count} selected feature(s), giving a {dataset_size.lower()} dataset profile.",
                (f"There are {len(numeric_columns)} numerical feature(s) for quantitative analysis, with about {avg_per_numeric:.1f} records per numerical feature."
                 if numeric_columns else "No numerical feature was selected for quantitative distribution analysis."),
            ],
        },
        "types": {
            "title": "2. Data Type & Feature Composition", "result": f"{len(numeric_columns)} numeric",
            "feature_composition": {
                "numerical": {"count": len(numeric_columns), "columns": numeric_columns},
                "categorical": {"count": len(categorical_columns), "columns": categorical_columns},
                "date_time": {"count": len(datetime_columns), "columns": datetime_columns},
            },
            "inferences": [
                f"{len(numeric_columns)} numerical feature(s) are available for statistical numerical analysis.",
                (f"{len(datetime_columns)} valid date/time feature(s) are available for temporal analysis."
                 if datetime_columns else "No valid date/time feature was selected, so time-series-specific analysis is limited."),
            ],
        },
        "distribution": {
            "title": "3. Distribution Analysis", "result": "Calculated",
            "distribution_statistics": distributions,
            "inferences": [
                (f"The average absolute skewness is {avg_abs_skew:.2f}, so the overall numerical distribution is approximately symmetric."
                 if avg_abs_skew <= .5 else f"The average absolute skewness is {avg_abs_skew:.2f}, indicating noticeable distribution asymmetry."),
                ("No feature exceeds an absolute skewness of 1, so strong distribution asymmetry is not dominant."
                 if all(abs(float(r["skewness"])) <= 1 for r in distributions)
                 else "At least one numerical feature exceeds an absolute skewness of 1 and should be treated as strongly skewed."),
            ],
        },
        "extreme": {
            "title": "4. Extreme Value Analysis", "result": f"{extreme_total} extreme",
            "iqr_analysis": extreme_rows,
            "inferences": [
                f"The IQR rule identifies {extreme_total} extreme observation(s) across the analyzed numerical features.",
                ("No IQR-extreme observations were detected." if extreme_total == 0
                 else "Extreme observations were detected and were retained during preprocessing."),
            ],
        },
        "scale": {
            "title": "5. Feature Scale Analysis", "result": scale_classification,
            "feature_scale": scale_rows, "range_ratio": round(scale_ratio, 4) if scale_ratio else None,
            "inferences": [
                (f"The largest-to-smallest non-zero feature-range ratio is {scale_ratio:.2f}×, giving an overall scale classification of {scale_classification.lower()}."
                 if scale_ratio else "A scale ratio could not be computed because no usable numerical ranges were available."),
                ("Distance-based methods can be sensitive to these range differences, so scale characteristics should be considered during model recommendation."
                 if scale_ratio > 10 else "The numerical feature ranges are relatively similar, reducing the need for aggressive scale correction."),
            ],
        },
        "correlation": {
            "title": "6. Correlation Analysis", "result": _relationship(strongest_corr) if correlation_rows else "Unavailable",
            "pearson_correlation": correlation_rows,
            "inferences": [
                (f"The strongest absolute Pearson correlation is {strongest_corr:.3f}, indicating an overall {_relationship(strongest_corr).lower()} linear relationship among numerical features."
                 if correlation_rows else "At least two numerical features are required for correlation analysis."),
                ("No feature pair reaches |r| ≥ 0.70, so strong linear redundancy is not dominant."
                 if correlation_rows and strongest_corr < .7 else
                 "At least one feature pair reaches |r| ≥ 0.70 and may contain substantial linear redundancy."),
            ],
        },
        "cluster": {
            "title": "7. Cluster Structure Analysis", "result": cluster_result["cluster_structure"],
            "cluster_analysis": cluster_result,
            "inferences": [
                (f"The best tested cluster count is {cluster_result['estimated_clusters']}, with a silhouette score of {cluster_result['silhouette_score']:.3f}."
                 if cluster_result["estimated_clusters"] is not None else cluster_result["reason"]),
                (f"The observed cluster structure is {cluster_result['cluster_structure'].lower()}, which can support local or cluster-aware anomaly analysis."
                 if cluster_result["estimated_clusters"] is not None else "Cluster-aware anomaly analysis should not be inferred without a valid cluster calculation."),
            ],
        },
        "density": {
            "title": "8. Local Density & Neighborhood Analysis", "result": density_result["local_density"],
            "density_analysis": density_result,
            "inferences": [
                (f"Nearest-neighbor distances have a coefficient of variation of {density_result['density_variability_cv']:.3f}, indicating {density_result['local_density'].lower()} local density."
                 if density_result["density_variability_cv"] is not None else "Nearest-neighbor density analysis was unavailable."),
                ("Some observations occupy sparser neighborhoods than others, which is useful evidence for local-neighborhood anomaly methods."
                 if density_result["local_density"] == "Variable" else "Neighborhood density appears relatively uniform in the standardized numerical space."),
            ],
        },
        "temporal": {
            "title": "9. Temporal Structure Analysis", "result": temporal["temporal_column"] or "Not detected",
            "temporal_structure": temporal,
            "inferences": [
                (f"The selected temporal column is {temporal['temporal_column']} with {temporal['valid_timestamps']} valid timestamp(s)."
                 if temporal_present else "No date/time column was selected, so temporal structure cannot be established."),
                ("Chronological ordering and interval regularity can be evaluated from the detected timestamps."
                 if temporal_present else "Time-series-specific characteristics will therefore remain unavailable."),
            ],
        },
        "timeseries": {
            "title": "10. Time-Series Pattern Analysis", "result": "Evaluated",
            "pattern_analysis": {
                key: ({"result": "Available", "evidence": evidence}
                      if temporal_present and numeric_columns
                      else {"result": "Unavailable", "evidence": "Requires a date/time column and numerical signal."})
                for key, evidence in [
                    ("sequential_subsequence", "A valid date/time column and numerical signal are present."),
                    ("periodic_signal", "Temporal observations and numerical signal can be evaluated for periodicity."),
                    ("shape_structure", "Temporal observations and numerical signal can be evaluated for sequence shape."),
                ]
            },
            "inferences": [
                ("Time-series pattern analysis has the required temporal and numerical prerequisites."
                 if temporal_present and numeric_columns else
                 "Time-series pattern analysis needs both a valid temporal column and at least one numerical signal."),
                ("Sequential, periodic and shape-pattern analysis can be used as evidence for later anomaly-model recommendation."
                 if temporal_present and numeric_columns else
                 "The missing prerequisite prevents reliable sequential, periodic and shape-pattern conclusions."),
            ],
        },
    }
    return {"analysis_completed": True, "records": row_count, "features": feature_count,
            "selected_columns": selected_columns, "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns, "datetime_columns": datetime_columns,
            "sections": sections}
