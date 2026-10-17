from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

try:
    import shap  # type: ignore
except Exception:
    shap = None


def _safe_float(value: Any) -> float | None:
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _value_text(value: Any) -> str | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float) and np.isfinite(value):
        return str(value)
    return str(value) if value is not None else None


def _unique_strings(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        if isinstance(value, str) and value.strip() and value.strip() not in out:
            out.append(value.strip())
    return out


def _full_model_name(value: Any) -> str:
    key = str(value or "").strip().lower()
    names = {
        "ecod": "Empirical Cumulative Distribution-based Outlier Detection (ECOD)",
        "empirical cumulative distribution-based outlier detection": "Empirical Cumulative Distribution-based Outlier Detection (ECOD)",
        "iforest": "Isolation Forest (IForest)",
        "isolation forest": "Isolation Forest (IForest)",
        "copod": "Copula-Based Outlier Detection (COPOD)",
        "copula-based outlier detection": "Copula-Based Outlier Detection (COPOD)",
        "knn": "K-Nearest Neighbors (KNN)",
        "k-nearest neighbors": "K-Nearest Neighbors (KNN)",
        "lof": "Local Outlier Factor (LOF)",
        "local outlier factor": "Local Outlier Factor (LOF)",
        "cblof": "Cluster-Based Local Outlier Factor (CBLOF)",
        "cluster-based local outlier factor": "Cluster-Based Local Outlier Factor (CBLOF)",
        "hbos": "Histogram-Based Outlier Score (HBOS)",
        "histogram-based outlier score": "Histogram-Based Outlier Score (HBOS)",
        "matrixprofile": "Matrix Profile",
        "matrix profile": "Matrix Profile",
        "spectralresidual": "Spectral Residual",
        "spectral residual": "Spectral Residual",
        "kshape": "K-Shape",
        "k-shape": "K-Shape",
    }
    return names.get(key, str(value or "Model"))


def _finite(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return values[np.isfinite(values)]


def _median(values: np.ndarray) -> float | None:
    values = _finite(values)
    return float(np.median(values)) if values.size else None


def _percentile(values: np.ndarray, value: float) -> float | None:
    values = np.sort(_finite(values))
    if values.size == 0 or not np.isfinite(value):
        return None
    return float(np.searchsorted(values, value, side="right") / values.size * 100.0)


def _robust_abs_z(values: np.ndarray, row_value: float) -> float:
    values = _finite(values)
    if values.size == 0 or not np.isfinite(row_value):
        return 0.0
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    scale = 1.4826 * mad
    if scale <= 1e-12:
        scale = float(np.std(values))
    return abs((row_value - median) / scale) if scale > 1e-12 else 0.0


def _fallback_contributions(
    X: np.ndarray,
    row_index: int,
    feature_names: list[str],
    feature_sources: list[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    row = np.asarray(X[row_index], dtype=float)
    for j, feature_name in enumerate(feature_names):
        value = float(row[j])
        typical = _median(X[:, j])
        contribution = _robust_abs_z(X[:, j], value)
        direction = (
            "high" if typical is not None and value > typical
            else "low" if typical is not None and value < typical
            else "typical"
        )
        result.append({
            "feature": feature_name,
            "source_column": feature_sources[j],
            "contribution": float(contribution),
            "method": "robust-deviation-evidence",
            "transformed_value": value,
            "direction": direction,
            "typical_value": typical,
            "percentile": _percentile(X[:, j], value),
        })
    return result


def _shap_contributions(
    model: Any,
    X: np.ndarray,
    row_index: int,
    feature_names: list[str],
    feature_sources: list[str],
) -> list[dict[str, Any]] | None:
    """Model-agnostic SHAP explanation of the fitted detector score."""
    if shap is None or len(X) < 2 or X.ndim != 2 or X.shape[1] == 0:
        return None
    if X.shape[1] > 40 or len(feature_names) != X.shape[1] or len(feature_sources) != X.shape[1]:
        return None
    if not 0 <= row_index < len(X) or not hasattr(model, "decision_function"):
        return None
    try:
        background_size = min(20, len(X))
        background_idx = np.linspace(0, len(X) - 1, background_size, dtype=int)
        background = X[background_idx]
        row = X[row_index:row_index + 1]

        def predict(data: np.ndarray) -> np.ndarray:
            return np.asarray(model.decision_function(np.asarray(data, dtype=float)), dtype=float).reshape(-1)

        explainer = shap.KernelExplainer(predict, background)
        shap_values = explainer.shap_values(
            row,
            nsamples=min(60, max(15, X.shape[1] * 3)),
        )
        values = np.asarray(shap_values, dtype=float)
        if values.ndim > 1:
            values = values[0]
        values = values.reshape(-1)
        if len(values) != len(feature_names):
            return None

        return [
            {
                "feature": feature_names[j],
                "source_column": feature_sources[j],
                "contribution": abs(float(values[j])),
                "signed_contribution": float(values[j]),
                "method": "SHAP",
                "transformed_value": float(row[0, j]),
                "direction": "increases_score" if values[j] > 0 else "decreases_score" if values[j] < 0 else "neutral",
                "typical_value": _median(X[:, j]),
                "percentile": _percentile(X[:, j], float(row[0, j])),
            }
            for j in range(len(feature_names))
        ]
    except Exception:
        return None


def _objective_text(objective: dict[str, Any] | None) -> str | None:
    if not isinstance(objective, dict):
        return None
    for key in ("objective", "user_objective", "objective_text", "understanding"):
        value = objective.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _human_feature_name(column: str) -> str:
    return str(column).replace("_", " ").strip().title()


def _feature_role(source: str, target_columns: list[str], explain_by_columns: list[str]) -> str:
    if source in target_columns:
        return "target"
    if source in explain_by_columns:
        return "explain_by_and_model_feature"
    return "model_feature"


def _contribution_strength(value: float, maximum: float) -> str:
    if maximum <= 0 or value <= 0:
        return "Low"
    ratio = value / maximum
    return "High" if ratio >= 0.66 else "Moderate" if ratio >= 0.33 else "Low"


def _direction_label(actual: Any, typical: Any, item: dict[str, Any]) -> str:
    signed = _safe_float(item.get("signed_contribution"))
    if item.get("method") == "SHAP" and signed is not None:
        return "High" if signed > 0 else "Low" if signed < 0 else "Typical"
    actual_num = _safe_float(actual)
    typical_num = _safe_float(typical)
    if actual_num is not None and typical_num is not None:
        return "High" if actual_num > typical_num else "Low" if actual_num < typical_num else "Typical"
    return str(item.get("direction") or "Typical").replace("_", " ").title()


def _column_roles(target_columns: list[str], explain_by_columns: list[str], feature_sources: list[str]) -> dict[str, Any]:
    targets = _unique_strings(target_columns)
    context = _unique_strings(explain_by_columns)
    sources = _unique_strings(feature_sources)
    source_set = set(sources)
    return {
        "target_columns": targets,
        "explain_by_columns": context,
        "model_feature_columns": sources,
        "target_columns_used_in_model": [x for x in targets if x in source_set],
        "explain_by_columns_used_in_model": [x for x in context if x in source_set],
        "explain_by_columns_context_only": [x for x in context if x not in source_set],
        "target_role": "Detection features selected for the anomaly detection model.",
        "explain_by_role": "Investigative/context columns used to identify and interpret records.",
    }


def _context_rows(raw_row: pd.Series, columns: list[str]) -> list[dict[str, Any]]:
    return [{"column": c, "label": _human_feature_name(c), "value": _value_text(raw_row.get(c))} for c in _unique_strings(columns)]


def _reference_statistics(
    reference_df: pd.DataFrame | None,
    columns: list[str],
) -> dict[str, dict[str, Any]]:
    """Return original-unit reference statistics for every selected target column."""
    if reference_df is None or not isinstance(reference_df, pd.DataFrame):
        return {}

    result: dict[str, dict[str, Any]] = {}

    for column in columns:
        if column not in reference_df.columns:
            continue

        series = reference_df[column]
        numeric = pd.to_numeric(series, errors="coerce")

        if numeric.notna().sum() >= max(2, int(len(series) * 0.5)):
            vals = numeric.dropna().to_numpy(dtype=float)
            if len(vals):
                result[column] = {
                    "type": "numeric",
                    "typical": float(np.median(vals)),
                    "values": vals,
                }
            continue

        clean = series.dropna()
        if len(clean):
            mode = clean.mode()
            result[column] = {
                "type": "categorical",
                "typical": mode.iloc[0] if len(mode) else clean.iloc[0],
                "values": clean.astype(str).to_numpy(),
            }

    return result


def _model_evidence(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        name = item.get("display_name") or item.get("model") or "Model"
        item["display_name"] = _full_model_name(name)
        result.append(item)
    return result


def _feature_interpretation(item: dict[str, Any], role: str) -> str:
    if item.get("method") == "SHAP":
        signed = _safe_float(item.get("signed_contribution")) or 0.0
        text = "The feature increased the model's anomaly score." if signed > 0 else "The feature decreased the model's anomaly score." if signed < 0 else "The feature had little directional effect on the model score."
    else:
        text = "The feature is statistically unusual relative to the reference distribution used for evidence."
    return text + " This is model/data evidence, not proof of causation."


def explain_record(
    model: Any,
    X: np.ndarray,
    row_index: int,
    feature_names: list[str],
    feature_sources: list[str],
    raw_row: pd.Series,
    target_columns: list[str],
    explain_by_columns: list[str],
    model_name: str,
    anomaly_score: float,
    threshold: float,
    model_evidence: list[dict[str, Any]] | None = None,
    objective: dict[str, Any] | None = None,
    reference_df: pd.DataFrame | None = None,
    record_status: str | None = None,
) -> dict[str, Any]:
    """Build a complete business-facing explanation for one normal/anomaly record.

    Every selected Target column is represented in ``target_feature_evidence``.
    Explain By columns remain context only and are never silently added to the
    detection model.
    """
    target_columns = _unique_strings(target_columns)
    explain_by_columns = _unique_strings(explain_by_columns)
    feature_names = list(feature_names or [])
    feature_sources = list(feature_sources or [])

    score = _safe_float(anomaly_score) or 0.0
    threshold_value = _safe_float(threshold) or 0.0

    supplied = str(record_status or "").strip().lower()
    if supplied in {"anomaly", "outlier", "1", "true"}:
        is_anomaly = True
    elif supplied in {"normal", "inlier", "0", "false"}:
        is_anomaly = False
    else:
        is_anomaly = score > threshold_value

    status = "Anomaly" if is_anomaly else "Normal"

    # SHAP is attempted when feasible; otherwise the explicitly-labelled
    # robust-deviation evidence is used.
    shap_items = _shap_contributions(
        model, X, row_index, feature_names, feature_sources
    )
    items = (
        shap_items
        if shap_items is not None
        else _fallback_contributions(
            X, row_index, feature_names, feature_sources
        )
    )
    method = "SHAP" if shap_items is not None else "robust-deviation-evidence"

    # Aggregate transformed/model features back to their original source columns.
    grouped: dict[str, float] = defaultdict(float)
    signed_grouped: dict[str, float] = defaultdict(float)
    representative: dict[str, dict[str, Any]] = {}

    for item in items:
        source = item.get("source_column")
        if not isinstance(source, str):
            continue
        contribution = _safe_float(item.get("contribution")) or 0.0
        grouped[source] += contribution
        signed_grouped[source] += _safe_float(
            item.get("signed_contribution")
        ) or 0.0
        representative.setdefault(source, item)

    ranked = sorted(grouped.items(), key=lambda x: x[1], reverse=True)
    total_contribution = sum(grouped.values())
    maximum = ranked[0][1] if ranked else 0.0

    refs = _reference_statistics(reference_df, target_columns)
    evidence_rows: list[dict[str, Any]] = []

    # IMPORTANT: iterate over Target columns, not only over transformed
    # feature evidence. This guarantees that every selected Target appears.
    for column in target_columns:
        item = representative.get(
            column,
            {
                "feature": column,
                "source_column": column,
                "method": method,
            },
        )

        actual = raw_row.get(column)
        actual_num = _safe_float(actual)
        ref = refs.get(column, {})

        if ref.get("type") == "numeric":
            values = np.asarray(ref.get("values", []), dtype=float)
            typical = _safe_float(ref.get("typical"))
            percentile = (
                _percentile(values, actual_num)
                if actual_num is not None and values.size
                else None
            )
        elif ref.get("type") == "categorical":
            values = np.asarray(ref.get("values", []), dtype=object)
            typical = ref.get("typical")
            percentile = None
        else:
            typical = _safe_float(item.get("typical_value"))
            percentile = _safe_float(item.get("percentile"))

        contribution = grouped.get(column, 0.0)
        signed = signed_grouped.get(column, 0.0)
        difference = (
            actual_num - typical
            if actual_num is not None and _safe_float(typical) is not None
            else None
        )
        typical_num = _safe_float(typical)
        difference_pct = (
            difference / abs(typical_num) * 100.0
            if difference is not None and abs(typical_num) > 1e-12
            else None
        )

        direction = _direction_label(
            actual,
            typical,
            {
                **item,
                "signed_contribution": signed,
            },
        )

        # If the detector did not expose a per-column attribution, use the
        # original-unit robust deviation as evidence for the UI bar.
        if contribution <= 0 and ref.get("type") == "numeric":
            values = np.asarray(ref.get("values", []), dtype=float)
            if actual_num is not None and values.size:
                contribution = _robust_abs_z(values, actual_num)

        evidence_rows.append(
            {
                "feature": item.get("feature") or column,
                "column": column,
                "source_column": column,
                "label": _human_feature_name(column),
                "value": _value_text(actual),
                "actual": _value_text(actual),
                "actual_value": _value_text(actual),
                "typical": typical,
                "typical_value": typical,
                "typical_value_display": _value_text(typical),
                "percentile": percentile,
                "difference_from_typical": difference,
                "difference_percent": difference_pct,
                "contribution": round(float(contribution), 6),
                "contribution_percent": (
                    round(float(contribution) / total_contribution * 100.0, 2)
                    if total_contribution > 0
                    else 0.0
                ),
                # Explicit SHAP fields used by the Objective-Based UI.
                # These are returned only from the actual SHAP calculation;
                # the frontend never recomputes the percentage.
                "shap_value": (
                    float(signed) if method == "SHAP" else None
                ),
                "shap_abs_value": (
                    float(contribution) if method == "SHAP" else None
                ),
                "total_shap_abs": (
                    float(total_contribution) if method == "SHAP" else None
                ),
                "shap_contribution_percent": (
                    round(float(contribution) / total_contribution * 100.0, 2)
                    if method == "SHAP" and total_contribution > 0
                    else None
                ),
                "contribution_strength": _contribution_strength(
                    float(contribution), maximum if maximum > 0 else float(contribution)
                ),
                "direction": direction,
                "signed_contribution": float(signed),
                "method": item.get("method", method),
                "role": _feature_role(
                    column, target_columns, explain_by_columns
                ),
                "interpretation": (
                    "The feature is unusually different from the reference "
                    "profile used for this explanation."
                    if contribution > 0
                    else "The feature is close to the reference profile."
                ),
            }
        )

    target_evidence = sorted(
        evidence_rows,
        key=lambda x: float(x.get("contribution", 0.0) or 0.0),
        reverse=True,
    )
    primary_item = target_evidence[0] if target_evidence else None

    # These are the exact source-column SHAP contributions used by the UI.
    # They are ranked from the clicked record's actual SHAP values.
    top_shap_features = (
        [
            {
                "feature": row["feature"],
                "column": row["column"],
                "label": row["label"],
                "shap_value": row.get("shap_value"),
                "shap_abs_value": row.get("shap_abs_value"),
                "total_shap_abs": row.get("total_shap_abs"),
                "shap_contribution_percent": row.get("shap_contribution_percent"),
                "direction": row["direction"],
            }
            for row in target_evidence
            if row.get("method") == "SHAP"
        ][:3]
        if method == "SHAP"
        else []
    )

    # Recompute strengths after every target column has been represented.
    for row in target_evidence:
        row["contribution_strength"] = _contribution_strength(
            float(row.get("contribution", 0.0) or 0.0),
            maximum if maximum > 0 else float(row.get("contribution", 0.0) or 0.0),
        )

    why_features = [
        {
            "column": row["column"],
            "feature": row["label"],
            "label": row["label"],
            "strength": row["contribution_strength"],
            "contribution": row["contribution"],
            "contribution_percent": row["contribution_percent"],
            "bar_percent": (
                round(
                    float(row["contribution"]) / maximum * 100.0,
                    1,
                )
                if maximum > 0
                else 4.0
            ),
            "direction": row["direction"],
            "actual": row["actual_value"],
            "typical": row["typical_value_display"],
        }
        for row in target_evidence[:10]
    ]

    score_gap = score - threshold_value
    gap_percent = (
        abs(score_gap) / abs(threshold_value) * 100.0
        if abs(threshold_value) > 1e-12
        else None
    )

    objective_text = _objective_text(objective)
    roles = _column_roles(
        target_columns, explain_by_columns, feature_sources
    )
    safe_models = _model_evidence(model_evidence)

    if is_anomaly:
        unusual = [
            row["label"].lower()
            for row in target_evidence
            if float(row.get("contribution", 0.0) or 0.0) > 0
        ][:3]

        if unusual:
            if len(unusual) == 1:
                explanation = (
                    f"This record differs substantially from the typical "
                    f"profile primarily because of {unusual[0]}."
                )
            else:
                explanation = (
                    "This record differs substantially from the typical "
                    f"profile primarily because of {', '.join(unusual[:-1])} "
                    f"and {unusual[-1]}."
                )
        else:
            explanation = (
                "This record differs substantially from the typical profile "
                "based on the selected detection features."
            )
    else:
        unusual = [
            row["label"].lower()
            for row in target_evidence
            if float(row.get("contribution", 0.0) or 0.0) > 0
        ][:2]
        if unusual:
            explanation = (
                f"This record remains within the normal detection range. "
                f"The most unusual selected feature"
                f"{'s' if len(unusual) > 1 else ''} "
                f"{'are' if len(unusual) > 1 else 'is'} "
                f"{' and '.join(unusual)}, but the overall score stays below "
                "the detection threshold."
            )
        else:
            explanation = (
                "This record remains within the normal detection range, "
                "with the selected features staying close to the typical profile."
            )

    return {
        "model": _full_model_name(model_name),
        "model_name": _full_model_name(model_name),
        "pyod_class": (
            str(model.__class__.__name__) if model is not None else None
        ),
        "anomaly_score": float(score),
        "threshold": float(threshold_value),
        "status": status,
        "is_anomaly": bool(is_anomaly),
        "threshold_gap": float(score_gap),
        "threshold_gap_percent": (
            float(gap_percent) if gap_percent is not None else None
        ),
        "threshold_relation": "above" if is_anomaly else "below",
        "above_threshold_percent": (
            float(gap_percent)
            if is_anomaly and gap_percent is not None
            else 0.0
        ),
        "below_threshold_percent": (
            float(gap_percent)
            if not is_anomaly and gap_percent is not None
            else 0.0
        ),
        "primary_contributing_feature": primary_item,
        "supporting_features": [
            {
                "column": row["column"],
                "label": row["label"],
                "contribution": row["contribution"],
                "contribution_percent": row["contribution_percent"],
                "value": row["actual_value"],
                "typical_value": row["typical_value"],
                "direction": row["direction"],
                "strength": row["contribution_strength"],
            }
            for row in target_evidence[1:6]
        ],
        "why_is_anomaly": why_features if is_anomaly else [],
        "why_is_normal": why_features if not is_anomaly else [],
        "feature_evidence": evidence_rows,
        "target_feature_evidence": target_evidence,
        "top_shap_features": top_shap_features,
        "shap_summary": {
            "available": method == "SHAP",
            "formula": "Contribution % = |Feature SHAP value| / sum(|All SHAP values|) * 100",
            "total_shap_abs": float(total_contribution) if method == "SHAP" else None,
            "top_features": top_shap_features,
        },
        "customer_vs_normal": [
            {
                "column": row["column"],
                "label": row["label"],
                "actual": row["actual_value"],
                "typical": row["typical_value_display"],
                "difference": row["difference_from_typical"],
                "difference_percent": row["difference_percent"],
            }
            for row in target_evidence
        ],
        "model_evidence": safe_models,
        "explain_by_context": _context_rows(
            raw_row, explain_by_columns
        ),
        "column_roles": roles,
        "objective_relation": {
            "objective": objective_text,
            "target_columns": target_columns,
            "explain_by_columns": explain_by_columns,
            "target_role": (
                "Target columns are the detection/model features used "
                "to produce the anomaly score."
            ),
            "explain_by_role": (
                "Explain By columns provide investigative context and "
                "are not silently added to detection."
            ),
            "causal_inference": False,
        },
        "business_explanation": explanation,
        "user_friendly_explanation": explanation,
        "narrative": explanation,
        "explanation": explanation,
        "explainability_method": method,
        "explainability_scope": {
            "model_level": method,
            "model_features": feature_sources,
            "target_columns": target_columns,
            "explain_by_columns": explain_by_columns,
            "causal_inference": False,
            "note": (
                "SHAP explains detector score behavior when available. "
                "Robust deviation is an explicitly labelled fallback."
            ),
        },
        "target_columns": target_columns,
        "explain_by_columns": explain_by_columns,
    }

