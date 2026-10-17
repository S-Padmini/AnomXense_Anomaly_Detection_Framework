
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phases.automatic_discovery.benchmark_engine import (
    MAX_BENCHMARK_ROWS,
    MAX_UNIVARIATE_BENCHMARK_UNITS,
    evaluation_indices,
    run_benchmark,
)
from app.phases.automatic_discovery.detection_engine import run_detection
from app.phases.automatic_discovery.model_compatibility import build_analysis_units
from app.scoring.empirical_benchmark_scorer import fixed_recommendations
from app.services.automatic_discovery_store import get_state, set_state


def get_phase3_data(session) -> tuple[pd.DataFrame, list[str]]:
    dataframe = getattr(session, "preprocessed_df", None)
    if dataframe is None:
        raise ValueError("Complete Phase 3 preprocessing before using Automatic Anomaly Discovery.")
    columns = list(getattr(session, "selected_columns", None) or [])
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Selected columns are missing from Phase 3 data: {missing}")
    if not columns:
        raise ValueError("No selected Phase 3 columns are available.")
    if len(dataframe) < 5:
        raise ValueError("At least five preprocessed records are required.")
    return dataframe, columns


def _config_key(session, columns: list[str]) -> tuple[Any, ...]:
    dataframe = getattr(session, "preprocessed_df", None)
    preprocess_result = getattr(session, "preprocess_result", None)
    return (
        id(dataframe),
        id(preprocess_result),
        len(dataframe) if dataframe is not None else 0,
        tuple(str(column) for column in columns),
    )


def _validate_state_for_session(
    state: dict[str, Any] | None,
    session,
    columns: list[str],
) -> dict[str, Any]:
    if not state or not state.get("benchmark"):
        raise ValueError("Click Model Recommendation and complete benchmarking first.")
    if state.get("config_key") != _config_key(session, columns):
        raise ValueError("Phase 3 data or selected columns changed. Run benchmarking again.")
    return state


def _sample_univariate_columns(columns: list[str], limit: int) -> list[str]:
    if len(columns) <= limit:
        return list(columns)
    indexes = np.linspace(0, len(columns) - 1, num=limit, dtype=np.int64)
    return [columns[int(index)] for index in indexes]


def benchmark_dataset(session, approach: str) -> dict[str, Any]:
    if approach not in {"univariate", "multivariate"}:
        raise ValueError("Approach must be univariate or multivariate.")

    dataframe, columns = get_phase3_data(session)
    row_indices = evaluation_indices(len(dataframe), MAX_BENCHMARK_ROWS)
    sampled_dataframe = dataframe.iloc[row_indices].loc[:, columns]

    benchmark_columns = (
        _sample_univariate_columns(columns, MAX_UNIVARIATE_BENCHMARK_UNITS)
        if approach == "univariate"
        else list(columns)
    )
    config_key = _config_key(session, columns)

    set_state(
        session.dataset_id,
        approach=approach,
        columns=list(columns),
        benchmark_columns=list(benchmark_columns),
        dataframe=dataframe,
        benchmark=None,
        detection=None,
        config_key=config_key,
    )

    units = build_analysis_units(sampled_dataframe, approach, benchmark_columns)
    benchmark = run_benchmark(units)

    set_state(
        session.dataset_id,
        approach=approach,
        columns=list(columns),
        benchmark_columns=list(benchmark_columns),
        dataframe=dataframe,
        benchmark=benchmark,
        detection=None,
        config_key=config_key,
    )

    return {
        "dataset_id": session.dataset_id,
        "approach": approach,
        "selected_columns": list(columns),
        "benchmark_columns": list(benchmark_columns),
        "benchmark_sampled_rows": len(sampled_dataframe),
        **benchmark,
    }


def get_recommendations(
    dataset_id: str,
    score_method: str,
    session=None,
) -> dict[str, Any]:
    if score_method not in {"best_score", "combined_score"}:
        raise ValueError("Choose best_score or combined_score.")

    state = get_state(dataset_id)
    if session is not None:
        _, columns = get_phase3_data(session)
        state = _validate_state_for_session(state, session, columns)
    elif not state or not state.get("benchmark"):
        raise ValueError("Click Model Recommendation and complete benchmarking first.")

    benchmark = state["benchmark"]
    stable_top_three = benchmark.get("top_three_recommendations") or fixed_recommendations(
        benchmark.get("results", []), 3
    )
    if len(stable_top_three) < 3:
        raise ValueError(
            "Automatic Discovery requires three successfully benchmarked models."
        )

    recommendations: list[dict[str, Any]] = []
    for rank, model in enumerate(stable_top_three[:3], start=1):
        item = dict(model)
        item["rank"] = rank
        item["display_score"] = item.get(score_method)
        item["display_score_method"] = score_method
        item["ensemble_weight_source"] = "combined_score"
        recommendations.append(item)

    return {
        "dataset_id": dataset_id,
        "approach": state["approach"],
        "score_method": score_method,
        "recommendations": recommendations,
        "benchmark_method": benchmark["benchmark_method"],
        "benchmark_rows": benchmark["benchmark_rows"],
        "benchmark_units": benchmark.get("benchmark_units", []),
        "metrics": benchmark["metrics"],
        "warning": benchmark["metrics"]["warning"],
        "errors": benchmark.get("errors", []),
        "ensemble_weight_source": (
            "The benchmark Combined Score of each fixed top-three model is "
            "normalized into its ensemble weight."
        ),
    }


def detect_dataset(
    session,
    score_method: str,
    contamination: float,
    selected_model: str | None = None,
) -> dict[str, Any]:
    if score_method not in {"best_score", "combined_score"}:
        raise ValueError("Choose best_score or combined_score.")

    dataframe, current_columns = get_phase3_data(session)
    state = _validate_state_for_session(
        get_state(session.dataset_id), session, current_columns
    )
    benchmark = state["benchmark"]
    top_three = benchmark.get("top_three_recommendations") or fixed_recommendations(
        benchmark.get("results", []), 3
    )
    if len(top_three) < 3:
        raise ValueError(
            "At least three successfully benchmarked models are required for Automatic Discovery."
        )

    top_three = [dict(item) for item in top_three[:3]]
    allowed_models = {str(item.get("model")) for item in top_three}

    if score_method == "combined_score":
        # Combined mode is intentionally strict: all three fixed recommendations
        # must be trained. A failed model is surfaced instead of silently reducing
        # the ensemble to two models.
        detection_models = top_three
        selected_model_for_result = None
    else:
        if not selected_model:
            raise ValueError("Select one of the three recommended models for Best Score detection.")
        if selected_model not in allowed_models:
            raise ValueError("Choose a model from the displayed top three recommendations.")
        detection_models = [
            item for item in top_three if str(item.get("model")) == selected_model
        ]
        selected_model_for_result = selected_model

    result = run_detection(
        dataframe=dataframe,
        approach=state["approach"],
        columns=current_columns,
        models=detection_models,
        contamination=float(contamination),
        score_method=score_method,
    )
    result["benchmark_method"] = benchmark["benchmark_method"]
    result["top_three_models"] = [str(item.get("model")) for item in top_three]
    result["selected_model"] = selected_model_for_result
    result["selected_model_rank"] = (
        next(
            (index + 1 for index, item in enumerate(top_three) if str(item.get("model")) == selected_model),
            None,
        )
        if selected_model_for_result
        else None
    )

    set_state(session.dataset_id, detection=result)
    return result
