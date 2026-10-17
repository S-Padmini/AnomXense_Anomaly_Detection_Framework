from __future__ import annotations

from typing import Any

import numpy as np

from app.phases.phase6.detection_engine import _model_fit_input as _model_fit_input_api
from app.phases.automatic_discovery.evaluation import evaluate_ml_detection
from fastapi import APIRouter, HTTPException, Query

from app.core.store import store
from app.schemas.automatic_discovery_schema import BenchmarkRequest, DetectionRequest
from app.services.automatic_discovery_service import (
    benchmark_dataset,
    detect_dataset,
    get_recommendations,
)
from app.services.automatic_discovery_store import clear_state, get_state

router = APIRouter(prefix="/api/automatic-discovery", tags=["Automatic Anomaly Discovery"])


def get_session(dataset_id: str):
    try:
        return store.get(dataset_id)
    except KeyError as exc:
        clear_state(dataset_id)
        raise HTTPException(status_code=404, detail="Dataset session not found or expired.") from exc


def get_detection(dataset_id: str) -> dict[str, Any]:
    get_session(dataset_id)
    state = get_state(dataset_id)
    if not state or not state.get("detection"):
        raise HTTPException(status_code=409, detail="Run Automatic Anomaly Discovery before requesting detection results.")
    return state["detection"]


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
        return value if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, (str, int, bool)):
        return value
    try:
        if hasattr(value, "isoformat"):
            return value.isoformat()
    except Exception:
        pass
    try:
        missing = np.asarray(value)
        if missing.ndim == 0 and bool(np.isnan(missing)):
            return None
    except Exception:
        pass
    return str(value)


def _model_summaries(detection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rank": index + 1,
            "model": model["model"],
            "benchmark_combined_score": float(model["benchmark_combined_score"]),
            "ensemble_weight": float(model["weight"]),
            "raw_score_min": float(model["raw_min"]),
            "raw_score_max": float(model["raw_max"]),
            "raw_score_direction": model.get("raw_score_direction", "Higher values are treated as more anomalous."),
        }
        for index, model in enumerate(detection["models"])
    ]


def _build_overview(detection: dict[str, Any]) -> dict[str, Any]:
    is_combined = detection["score_method"] == "combined_score"
    ensemble = detection.get("ensemble")
    model_names = [str(item["model"]) for item in detection.get("models", [])]
    if is_combined:
        model_label = ", ".join(model_names)
        detection_model = "Ensemble"
    else:
        model_label = detection.get("selected_model") or (model_names[0] if model_names else None)
        detection_model = "Single Model"

    overview: dict[str, Any] = {
        "approach": (
            "ML approach - Univariate"
            if detection["approach"] == "univariate"
            else "ML approach - Multivariate"
        ),
        "approach_key": detection["approach"],
        "score_method": detection["score_method"],
        "detection_mode": "Best Score" if not is_combined else "Ensemble Mode",
        "detection_model": detection_model,
        "model_used": model_label,
        "model": detection.get("model_name"),
        "selected_model": detection.get("selected_model"),
        "top_three_models": detection.get("top_three_models", []),
        "total_records": int(detection["total_records_processed"]),
        "anomaly_records": int(detection["anomaly_records_count"]),
        "normal_records": int(detection["normal_record_count"]),
        "anomaly_rate_percent": round(float(detection["anomaly_rate"]), 4),
        "selected_columns": list(detection.get("columns", [])),
        "contamination": float(ensemble["contamination"]) if ensemble else float(detection.get("contamination", 0.10)),
        "models": _model_summaries(detection),
        "accuracy": (
            float(detection["accuracy"])
            if detection.get("accuracy") is not None
            else None
        ),
    }
    if ensemble:
        overview["threshold"] = float(ensemble["threshold"])
        overview["ensemble"] = {
            "threshold": float(ensemble["threshold"]),
            "contamination": float(ensemble["contamination"]),
            "model_count": len(model_names),
        }
    else:
        # Best Score has a native threshold in multivariate mode.
        if detection["approach"] == "multivariate":
            overview["threshold"] = float(detection["models"][0]["unit_results"][0]["threshold"])
        else:
            overview["threshold"] = None
        overview["ensemble"] = None
    return overview


def _unit_by_name(detection: dict[str, Any], column_name: str | None) -> dict[str, Any] | None:
    if detection["approach"] != "univariate" or not column_name:
        return None
    for model in detection["models"]:
        for unit in model["unit_results"]:
            if unit["unit"] == column_name:
                return unit
    return None


def _column_ensemble_view(detection: dict[str, Any], column_name: str) -> tuple[np.ndarray, np.ndarray, float, list[dict[str, Any]]]:
    if detection["score_method"] == "best_score":
        unit = _unit_by_name(detection, column_name)
        if unit is None:
            raise ValueError(f"Column '{column_name}' was not selected for detection.")
        return (
            np.asarray(unit["raw_scores"], dtype=np.float64),
            np.asarray(unit["labels"], dtype=np.uint8),
            float(unit["threshold"]),
            [{"model": detection["models"][0]["model"], "raw_score": np.asarray(unit["raw_scores"], dtype=np.float64), "normalized_score": None, "weight": 1.0, "benchmark_combined_score": detection["models"][0]["benchmark_combined_score"]}],
        )

    model_views = []
    for model in detection["models"]:
        unit = next((u for u in model["unit_results"] if u["unit"] == column_name), None)
        if unit is None:
            raise ValueError(f"Column '{column_name}' is missing from model {model['model']} results.")
        raw = np.asarray(unit["raw_scores"], dtype=np.float64)
        minimum = float(raw.min())
        maximum = float(raw.max())
        normalized = np.zeros_like(raw) if maximum <= minimum else (raw - minimum) / (maximum - minimum)
        model_views.append({
            "model": model["model"],
            "raw_score": raw,
            "normalized_score": normalized,
            "weight": float(model["weight"]),
            "benchmark_combined_score": float(model["benchmark_combined_score"]),
            "native_threshold": float(unit["threshold"]),
        })

    ensemble_scores = np.zeros_like(model_views[0]["normalized_score"])
    for view in model_views:
        ensemble_scores += view["weight"] * view["normalized_score"]
    threshold = float(np.quantile(ensemble_scores, 1.0 - float(detection["ensemble"]["contamination"])))
    labels = (ensemble_scores > threshold).astype(np.uint8)
    return ensemble_scores, labels, threshold, model_views


def _build_records_page(
    detection: dict[str, Any],
    *,
    page: int = 1,
    page_size: int = 50,
    anomalies_only: bool = False,
    column_name: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    if page < 1 or not 1 <= page_size <= 500:
        raise ValueError("Invalid page or page_size.")

    dataframe = detection["dataframe"]
    if column_name is not None:
        if detection["approach"] != "univariate" or column_name not in detection.get("columns", []):
            raise ValueError(f"Column '{column_name}' is not available for univariate results.")
        scores, labels, threshold, model_views = _column_ensemble_view(detection, column_name)
        values_columns = [column_name]
    else:
        scores = np.asarray([record["anomaly_score"] for record in detection["records"]], dtype=np.float64)
        labels = np.asarray([1 if record["status"] == "Anomaly" else 0 for record in detection["records"]], dtype=np.uint8)
        threshold = None
        if detection.get("ensemble"):
            threshold = float(detection["ensemble"]["threshold"])
        elif detection["approach"] == "multivariate":
            threshold = float(detection["models"][0]["unit_results"][0]["threshold"])
        model_views = []
        values_columns = list(detection.get("columns", []))

    candidate_indices = np.flatnonzero(labels == 1) if anomalies_only else np.arange(len(scores), dtype=np.int64)

    if search and str(search).strip():
        term = str(search).strip().casefold()
        search_values = values_columns
        keep: list[int] = []
        for raw_idx in candidate_indices:
            idx = int(raw_idx)
            record_number = str(idx + 1)
            score_text = str(float(scores[idx]))
            if term in record_number.casefold() or term in score_text.casefold():
                keep.append(idx)
                continue
            for col in search_values:
                value_text = _json_safe(dataframe.iloc[idx][col])
                if term in str(value_text).casefold():
                    keep.append(idx)
                    break
        candidate_indices = np.asarray(keep, dtype=np.int64)
    total = len(candidate_indices)
    start = (page - 1) * page_size
    selected = candidate_indices[start:start + page_size]
    records = []
    for index in selected:
        idx = int(index)
        row = {
            "record_number": idx + 1,
            "source_index": _json_safe(dataframe.index[idx]),
            "values": {str(column): _json_safe(dataframe.iloc[idx][column]) for column in values_columns},
            "anomaly_score": float(scores[idx]),
            "threshold": float(threshold) if threshold is not None else None,
            "status": "Anomaly" if labels[idx] else "Normal",
        }
        if model_views:
            row["model_scores"] = [
                {
                    "model": view["model"],
                    "raw_score": float(view["raw_score"][idx]),
                    "normalized_score": None if view["normalized_score"] is None else float(view["normalized_score"][idx]),
                    "weight": float(view["weight"]),
                    "benchmark_combined_score": float(view["benchmark_combined_score"]),
                }
                for view in model_views
            ]
        records.append(row)

    return {
        "page": page,
        "page_size": page_size,
        "total_matching_records": int(total),
        "total_pages": (total + page_size - 1) // page_size,
        "anomalies_only": bool(anomalies_only),
        "column": column_name,
        "search": search or "",
        "records": records,
    }


def _build_column_summaries(detection: dict[str, Any]) -> list[dict[str, Any]]:
    if detection["approach"] != "univariate":
        return []
    summaries = []
    for column in detection["columns"]:
        scores, labels, threshold, model_views = _column_ensemble_view(detection, column)
        summaries.append({
            "column": column,
            "total_records": len(scores),
            "anomaly_records": int(labels.sum()),
            "normal_records": int(len(scores) - labels.sum()),
            "anomaly_rate_percent": round(100.0 * float(labels.mean()), 4),

        })
    return summaries


@router.post("/{dataset_id}/benchmark")
def benchmark(dataset_id: str, request: BenchmarkRequest):
    session = get_session(dataset_id)
    try:
        return benchmark_dataset(session, request.approach)
    except (ValueError, RuntimeError, ImportError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/recommendations")
def recommendations(
    dataset_id: str,
    score_method: str = Query(default="combined_score", pattern="^(best_score|combined_score)$"),
):
    session = get_session(dataset_id)
    try:
        return get_recommendations(dataset_id, score_method, session=session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{dataset_id}/detect")
def detect(dataset_id: str, request: DetectionRequest):
    session = get_session(dataset_id)
    try:
        result = detect_dataset(
            session=session,
            score_method=request.score_method,
            contamination=request.effective_contamination(),
            selected_model=request.selected_model,
        )

        evaluation = evaluate_ml_detection(
            dataframe=result["dataframe"],
            detection=result,
        )

        result["accuracy"] = float(evaluation["accuracy"])

        response: dict[str, Any] = {
            "dataset_id": dataset_id,
            "summary": _build_overview(result),
        }
        if result["approach"] == "univariate":
            response["column_summaries"] = _build_column_summaries(result)
        return response
    except (ValueError, RuntimeError, ImportError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{dataset_id}/result")
def result(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    anomalies_only: bool = False,
    search: str | None = Query(default=None, max_length=200),
):
    detection = get_detection(dataset_id)
    response: dict[str, Any] = {
        "dataset_id": dataset_id,
        "summary": _build_overview(detection),
        "records_page": _build_records_page(detection, page=page, page_size=page_size, anomalies_only=anomalies_only, search=search),
    }
    if detection["approach"] == "univariate":
        response["column_summaries"] = _build_column_summaries(detection)
    return response


@router.get("/{dataset_id}/result/columns/{column_name:path}")
def column_result(
    dataset_id: str,
    column_name: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    anomalies_only: bool = False,
    search: str | None = Query(default=None, max_length=200),
):
    detection = get_detection(dataset_id)
    if detection["approach"] != "univariate":
        raise HTTPException(status_code=400, detail="Column-specific results are only available for univariate detection.")
    try:
        return {
            "dataset_id": dataset_id,
            "column": column_name,
            "summary": _build_overview(detection),
            "column_summary": next(item for item in _build_column_summaries(detection) if item["column"] == column_name),
            "records_page": _build_records_page(detection, page=page, page_size=page_size, anomalies_only=anomalies_only, column_name=column_name, search=search),
        }
    except (ValueError, StopIteration) as exc:
        raise HTTPException(status_code=404, detail=str(exc) or "Column not found.") from exc


@router.get("/{dataset_id}/anomaly/{record_number}")
def anomaly_detail(dataset_id: str, record_number: int, column_name: str | None = None):
    detection = get_detection(dataset_id)
    if not 1 <= record_number <= len(detection["records"]):
        raise HTTPException(status_code=404, detail="Record not found.")
    index = record_number - 1
    dataframe = detection["dataframe"]

    if column_name:
        try:
            scores, labels, threshold, model_views = _column_ensemble_view(detection, column_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        score = float(scores[index])
        status = "Anomaly" if labels[index] else "Normal"
        values_columns = [column_name]
    else:
        score = float(detection["records"][index]["anomaly_score"])
        threshold = detection["records"][index].get("threshold")
        status = detection["records"][index]["status"]
        model_views = []
        if detection["approach"] == "multivariate":
            model_views = []
            for model in detection["models"]:
                unit = model["unit_results"][0]
                raw = float(unit["raw_scores"][index])
                normalized = None
                if detection["score_method"] == "combined_score":
                    minimum = float(unit["raw_scores"].min())
                    maximum = float(unit["raw_scores"].max())
                    normalized = 0.0 if maximum <= minimum else (raw - minimum) / (maximum - minimum)
                model_views.append({
                    "model": model["model"],
                    "raw_score": raw,
                    "normalized_score": normalized,
                    "weight": float(model["weight"]),
                    "benchmark_combined_score": float(model["benchmark_combined_score"]),
                })
        values_columns = list(detection.get("columns", []))

    return {
        "record_number": record_number,
        "source_index": _json_safe(dataframe.index[index]),
        "status": status,
        "anomaly_score": score,
        "threshold": None if threshold is None else float(threshold),
        "values": {str(column): _json_safe(dataframe.iloc[index][column]) for column in values_columns},
    }


@router.get("/{dataset_id}/visualization")
def visualization(
    dataset_id: str,
    column_name: str | None = None,
    limit: int = Query(default=1000, ge=50, le=5000),
    plot_type: str = Query(default="score_distribution", pattern="^(score_distribution|feature_vs_score|parallel_coordinates)$"),
):
    detection = get_detection(dataset_id)
    dataframe = detection["dataframe"]
    if column_name:
        if detection["approach"] != "univariate" or column_name not in detection.get("columns", []):
            raise HTTPException(status_code=400, detail="Provide a valid selected univariate column_name.")
        scores, labels, threshold, _ = _column_ensemble_view(detection, column_name)
    else:
        scores = np.asarray([record["anomaly_score"] for record in detection["records"]], dtype=np.float64)
        labels = np.asarray([1 if record["status"] == "Anomaly" else 0 for record in detection["records"]], dtype=np.uint8)
        threshold = detection.get("ensemble", {}).get("threshold") if detection.get("ensemble") else (
            detection["models"][0]["unit_results"][0]["threshold"] if detection["approach"] == "multivariate" else None
        )

    n_rows = len(scores)
    indexes = np.linspace(0, n_rows - 1, num=limit, dtype=np.int64) if n_rows > limit else np.arange(n_rows, dtype=np.int64)
    points: list[dict[str, Any]] = []
    for index in indexes:
        idx = int(index)
        point: dict[str, Any] = {
            "record_number": idx + 1,
            "anomaly_score": float(scores[idx]),
            "threshold": None if threshold is None else float(threshold),
            "status": "Anomaly" if labels[idx] else "Normal",
        }
        if column_name:
            point["column"] = column_name
            point["value"] = _json_safe(dataframe.iloc[idx][column_name])
        else:
            point["values"] = {str(column): _json_safe(dataframe.iloc[idx][column]) for column in detection.get("columns", [])}
        points.append(point)

    return {
        "approach": detection["approach"],
        "score_method": detection["score_method"],
        "score_type": "ensemble_score" if detection["score_method"] == "combined_score" else "model_score",
        "selected_model": detection.get("selected_model"),
        "threshold": None if threshold is None else float(threshold),
        "total_records": int(n_rows),
        "displayed_records": int(len(indexes)),
        "sampling_applied": bool(n_rows > limit),
        "plot_type": plot_type,
        "points": points,
    }


@router.get("/{dataset_id}/feature-contribution/{record_number}")
def feature_contribution(dataset_id: str, record_number: int, top_n: int = Query(default=3, ge=1, le=20)):
    detection = get_detection(dataset_id)
    if not 1 <= record_number <= len(detection["records"]):
        raise HTTPException(status_code=404, detail="Record not found.")

    index = record_number - 1
    contributions: list[dict[str, Any]] = []

    # Model-agnostic local ablation: replace all transformed dimensions belonging
    # to one original feature by that feature's median/baseline in feature space,
    # then measure the change in the same detector score used to calculate the
    # existing feature-contribution percentages.
    model_results = detection.get("models", [])
    for model_result in model_results:
        units = model_result.get("unit_results", [])
        for unit in units:
            estimator = unit.get("model")
            if estimator is None:
                continue

            X = np.asarray(
                unit.get("X") if unit.get("X") is not None else [],
                dtype=np.float64,
            )
            if X.ndim != 2 or len(X) == 0:
                # X is intentionally not serialized in API responses but remains
                # available in the in-memory detection state.
                X = None
            if X is None:
                continue

            sources = list(unit.get("feature_sources", []))
            original_input = _model_input_for_api(
                model_result["model"], X[index:index + 1]
            )
            original_score = float(
                np.asarray(
                    estimator.decision_function(original_input)
                ).reshape(-1)[0]
            )

            for column in unit.get("columns", []):
                feature_indexes = [
                    j for j, source in enumerate(sources) if source == column
                ]
                if not feature_indexes:
                    continue

                perturbed = X[index:index + 1].copy()
                baseline = np.median(X[:, feature_indexes], axis=0)
                perturbed[0, feature_indexes] = baseline

                perturbed_input = _model_input_for_api(
                    model_result["model"], perturbed
                )
                perturbed_score = float(
                    np.asarray(
                        estimator.decision_function(perturbed_input)
                    ).reshape(-1)[0]
                )

                score_change = abs(original_score - perturbed_score)

                contributions.append({
                    "feature": str(column),
                    "original_score": original_score,
                    "perturbed_score": perturbed_score,
                    "score_change": score_change,
                    "raw_delta": score_change,
                    "model": model_result["model"],
                })

    if not contributions:
        raise HTTPException(
            status_code=422,
            detail="Feature contribution analysis is not available for this detection result.",
        )

    # Aggregate across models/units. For Combined Score, the same model weights
    # used by the existing contribution calculation are applied to every
    # intermediate score and score change. For Best Score there is one model
    # with weight 1.0.
    by_feature: dict[str, dict[str, float]] = {}

    for item in contributions:
        model_name = item["model"]
        model_weight = next(
            (
                float(m.get("weight", 1.0))
                for m in model_results
                if m.get("model") == model_name
            ),
            1.0,
        )

        feature = item["feature"]
        bucket = by_feature.setdefault(
            feature,
            {
                "original_score": 0.0,
                "perturbed_score": 0.0,
                "score_change": 0.0,
            },
        )

        bucket["original_score"] += (
            float(item["original_score"]) * model_weight
        )
        bucket["perturbed_score"] += (
            float(item["perturbed_score"]) * model_weight
        )
        bucket["score_change"] += (
            float(item["score_change"]) * model_weight
        )

    total = sum(
        values["score_change"] for values in by_feature.values()
    )

    ranked = sorted(
        by_feature.items(),
        key=lambda pair: pair[1]["score_change"],
        reverse=True,
    )

    rows = []
    for rank, (feature, values) in enumerate(ranked, start=1):
        contribution_percent = (
            100.0 * values["score_change"] / total
            if total > 0
            else 0.0
        )

        rows.append({
            "rank": rank,
            "feature": feature,

            # Existing field retained for the current frontend.
            "contribution_percent": round(contribution_percent, 4),

            # Detailed values used by the clickable explanation panel.
            "original_score": round(values["original_score"], 8),
            "perturbed_score": round(values["perturbed_score"], 8),
            "score_change": round(values["score_change"], 8),
            "total_score_change": round(total, 8),
            "contribution_percentage": round(contribution_percent, 4),
        })

    return {
        "record_number": record_number,
        "status": detection["records"][index]["status"],
        "anomaly_score": float(detection["records"][index]["anomaly_score"]),
        "threshold": detection["records"][index].get("threshold"),
        "method": "Model-agnostic local feature ablation",
        "top_contributing_attributes": rows[:top_n],
        "all_feature_contributions": rows,
        "total_score_change": round(total, 8),
    }



def _model_input_for_api(model_name: str, X: np.ndarray) -> np.ndarray:
    # Keep the same estimator input convention as final detection.
    return _model_fit_input_api(model_name, X)
