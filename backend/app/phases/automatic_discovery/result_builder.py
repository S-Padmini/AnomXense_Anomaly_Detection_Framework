from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (str, int, float, bool)):
        return value if not isinstance(value, float) or np.isfinite(value) else None
    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and missing:
            return None
    except Exception:
        pass
    return str(value)


def build_overview(detection: dict[str, Any], score_method: str | None = None) -> dict[str, Any]:
    method = score_method or detection.get("score_method", "combined_score")
    combined = method == "combined_score"
    ensemble = detection.get("ensemble")
    return {
        "approach": detection["approach"],
        "score_method": method,
        "model_mode": "three_model_ensemble" if combined else "single_model",
        "model": detection.get("model_name"),
        "selected_model": detection.get("selected_model"),
        "top_three_models": detection.get("top_three_models", []),
        "total_records": int(detection["total_records_processed"]),
        "anomaly_records": int(detection["anomaly_records_count"]),
        "normal_records": int(detection["normal_record_count"]),
        "anomaly_rate_percent": round(float(detection["anomaly_rate"]), 4),
        "selected_columns": list(detection.get("columns", [])),
        "models": [
            {
                "rank": index + 1,
                "model": item["model"],
                "benchmark_combined_score": float(item["benchmark_combined_score"]),
                "ensemble_weight": float(item["weight"]),
            }
            for index, item in enumerate(detection["models"])
        ],
        "ensemble": None if not ensemble else {
            "normalization": ensemble["normalization"],
            "normalization_formula": ensemble["formula"],
            "weight_formula": ensemble["weight_formula"],
            "score_formula": ensemble["score_formula"],
            "threshold_formula": ensemble["threshold_formula"],
            "weights_sum": float(ensemble["weights_sum"]),
            "threshold": float(ensemble["threshold"]),
            "contamination": float(ensemble["contamination"]),
        },
        "score_source": detection.get("score_source"),
    }


def _unit(detection: dict[str, Any], column_name: str | None = None) -> dict[str, Any]:
    if detection["approach"] == "multivariate":
        return detection["models"][0]["unit_results"][0]
    if not column_name:
        raise ValueError("Provide a column_name for univariate results.")
    for model in detection["models"]:
        for item in model["unit_results"]:
            if item["unit"] == column_name:
                return item
    raise ValueError(f"Column '{column_name}' was not selected.")


def build_column_summaries(detection: dict[str, Any]) -> list[dict[str, Any]]:
    if detection["approach"] != "univariate":
        return []
    output = []
    for column in detection["columns"]:
        if detection["score_method"] == "best_score":
            unit = _unit(detection, column)
            labels = np.asarray(unit["labels"], dtype=np.uint8)
            threshold = float(unit["threshold"])
            model_count = 1
        else:
            views = []
            for model in detection["models"]:
                unit = _unit({**detection, "models": [model]}, column)
                raw = np.asarray(unit["raw_scores"], dtype=np.float64)
                lo, hi = float(raw.min()), float(raw.max())
                normalized = np.zeros_like(raw) if hi <= lo else (raw - lo) / (hi - lo)
                views.append((float(model["weight"]), normalized))
            ensemble = sum(weight * score for weight, score in views)
            threshold = float(np.quantile(ensemble, 1.0 - float(detection["ensemble"]["contamination"])))
            labels = (ensemble > threshold).astype(np.uint8)
            model_count = 3
        total = len(labels)
        output.append({
            "column": column,
            "total_records": total,
            "anomaly_records": int(labels.sum()),
            "normal_records": int(total - labels.sum()),
            "anomaly_rate_percent": round(100.0 * float(labels.mean()), 4) if total else 0.0,
            "threshold": threshold,
            "model_count": model_count,
        })
    return output
