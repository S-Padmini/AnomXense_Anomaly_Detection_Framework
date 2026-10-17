from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from fastapi.responses import (
    StreamingResponse,
)

from app.core.store import store

from app.phases.phase6.detection_engine import (
    run_detection,
)

from app.phases.phase6.report_generator import (
    generate_report,
)

from app.schemas.phase6_schema import (
    DetectionRequest,
    FilterRequest,
    Phase6Response,
)


router = APIRouter(
    prefix="/api/phase6",
    tags=[
        "Phase 6"
    ],
)


# ============================================================
# MODEL DISPLAY NAMES
# ============================================================

MODEL_DISPLAY_NAMES = {
    "ECOD":
        "Empirical Cumulative Distribution-based Outlier Detection",

    "Empirical Cumulative Distribution-based Outlier Detection":
        "Empirical Cumulative Distribution-based Outlier Detection",

    "IForest":
        "Isolation Forest",

    "IsolationForest":
        "Isolation Forest",

    "Isolation Forest":
        "Isolation Forest",

    "COPOD":
        "Copula-Based Outlier Detection",

    "Copula-Based Outlier Detection":
        "Copula-Based Outlier Detection",

    "KNN":
        "K-Nearest Neighbors",

    "K-Nearest Neighbors":
        "K-Nearest Neighbors",

    "LOF":
        "Local Outlier Factor",

    "Local Outlier Factor":
        "Local Outlier Factor",

    "CBLOF":
        "Cluster-Based Local Outlier Factor",

    "Cluster-Based Local Outlier Factor":
        "Cluster-Based Local Outlier Factor",

    "HBOS":
        "Histogram-Based Outlier Score",

    "Histogram-Based Outlier Score":
        "Histogram-Based Outlier Score",

    "MatrixProfile":
        "Matrix Profile",

    "Matrix Profile":
        "Matrix Profile",

    "SpectralResidual":
        "Spectral Residual",

    "Spectral Residual":
        "Spectral Residual",

    "KShape":
        "K-Shape",

    "K-Shape":
        "K-Shape",
}


def _full_model_name(
    model: Any,
) -> str:

    if model is None:
        return ""

    text = str(
        model
    ).strip()

    return MODEL_DISPLAY_NAMES.get(
        text,
        text,
    )


# ============================================================
# SESSION
# ============================================================

def _get_session(
    dataset_id: str,
) -> Any:

    try:

        session = (
            store.get(
                dataset_id
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset session "
                f"'{dataset_id}' "
                "was not found."
            ),
        ) from exc

    if session is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset session "
                f"'{dataset_id}' "
                "was not found."
            ),
        )

    return session


# ============================================================
# GENERIC SESSION ACCESS
# ============================================================

def _first_attr(
    session: Any,
    names: list[str],
) -> Any:

    if isinstance(
        session,
        dict,
    ):

        for name in names:

            if (
                name in session
                and
                session[name] is not None
            ):

                return session[name]

        return None

    for name in names:

        value = getattr(
            session,
            name,
            None,
        )

        if value is not None:
            return value

    return None


def _set_attr(
    session: Any,
    name: str,
    value: Any,
) -> None:

    if isinstance(
        session,
        dict,
    ):

        session[name] = value
        return

    setattr(
        session,
        name,
        value,
    )


# ============================================================
# DATAFRAME
# ============================================================

def _as_dataframe(
    value: Any,
) -> pd.DataFrame | None:

    if isinstance(
        value,
        pd.DataFrame,
    ):

        return value.copy()

    if isinstance(
        value,
        list,
    ):

        try:

            return pd.DataFrame(
                value
            )

        except Exception:

            return None

    if isinstance(
        value,
        dict,
    ):

        for key in (
            "data",
            "records",
            "rows",
        ):

            if key in value:

                try:

                    return pd.DataFrame(
                        value[key]
                    )

                except Exception:

                    continue

    return None


# ============================================================
# LOAD DATASET
# ============================================================

def _load_dataframe(
    session: Any,
) -> pd.DataFrame:

    # Phase 6 MUST consume the dataframe produced by Phase 3.
    # Processed candidates are deliberately checked before the
    # original uploaded dataframe.
    candidates = [

        "preprocessed_df",
        "processed_df",
        "preprocessed_data",
        "processed_data",
    ]

    for name in candidates:

        frame = (
            _as_dataframe(
                _first_attr(
                    session,
                    [name],
                )
            )
        )

        if (
            frame is not None
            and
            not frame.empty
        ):

            return frame

    # Some Phase 3 implementations store the processed dataframe
    # inside a preprocessing-result dictionary.
    preprocessing_results = [
        "preprocess_result",
        "phase3_preprocess_result",
        "preprocessing_result",
        "phase3_result",
    ]

    for result_name in preprocessing_results:
        result_value = _first_attr(
            session,
            [result_name],
        )

        if not isinstance(result_value, dict):
            continue

        for key in (
            "preprocessed_df",
            "processed_df",
            "preprocessed_data",
            "processed_data",
            "dataframe",
            "df",
            "data",
        ):
            frame = _as_dataframe(
                result_value.get(key)
            )

            if (
                frame is not None
                and
                not frame.empty
            ):
                return frame

    # Compatibility fallback for an older session that does not
    # contain an explicit Phase 3 dataframe.
    candidates = [
        "dataframe",
        "df",
        "raw_df",
        "data",
        "raw_data",
        "dataset",
    ]

    for name in candidates:
        frame = _as_dataframe(
            _first_attr(session, [name])
        )

        if (
            frame is not None
            and
            not frame.empty
        ):
            return frame

    path_value = (
        _first_attr(
            session,
            [
                "file_path",
                "uploaded_file_path",
                "path",
                "source_path",
                "dataset_path",
            ],
        )
    )

    if path_value:

        path = Path(
            str(
                path_value
            )
        )

        if path.exists():

            suffix = (
                path.suffix.lower()
            )

            if suffix in {
                ".xlsx",
                ".xls",
            }:

                return pd.read_excel(
                    path
                )

            return pd.read_csv(
                path
            )

    raise HTTPException(
        status_code=500,
        detail=(
            "Phase 6 could not locate "
            "the uploaded dataset inside "
            "the existing DatasetSession."
        ),
    )


# ============================================================
# ORIGINAL DATASET (REPORT LINEAGE)
# ============================================================

def _load_original_dataframe(
    session: Any,
) -> pd.DataFrame | None:
    """Return the original uploaded dataframe when it is available.

    Phase 6 detection intentionally uses the Phase 3 processed dataframe.
    This helper is report lineage only, so it never changes the detection
    dataframe or detection behaviour.
    """
    candidates = [
        "raw_df",
        "raw_data",
        "original_df",
        "original_data",
        "uploaded_df",
        "uploaded_data",
        "dataframe",
        "df",
        "data",
        "dataset",
    ]

    for name in candidates:
        frame = _as_dataframe(_first_attr(session, [name]))
        if frame is not None and not frame.empty:
            return frame.copy()

    path_value = _first_attr(
        session,
        [
            "file_path",
            "uploaded_file_path",
            "path",
            "source_path",
            "dataset_path",
        ],
    )

    if path_value:
        path = Path(str(path_value))
        if path.exists():
            suffix = path.suffix.lower()
            try:
                if suffix in {".xlsx", ".xls"}:
                    return pd.read_excel(path)
                return pd.read_csv(path)
            except Exception:
                return None

    return None


def _phase3_preprocessing_metadata(
    session: Any,
) -> dict[str, Any]:
    """Expose the stored Phase 3 preprocessing metadata to the report."""
    candidates = [
        "preprocess_result",
        "phase3_preprocess_result",
        "preprocessing_result",
        "phase3_result",
        "preprocessing",
        "preprocessing_summary",
    ]

    for name in candidates:
        value = _first_attr(session, [name])
        if not isinstance(value, dict):
            continue

        # Some Phase 3 implementations wrap the actual preprocessing result.
        nested = (
            value.get("preprocessing")
            or value.get("preprocessing_summary")
            or value.get("result")
        )
        if isinstance(nested, dict):
            return nested
        return value

    return {}

# ============================================================
# PHASE 2 COLUMN POOL
# ============================================================

def _phase2_selected_columns(
    session: Any,
    df: pd.DataFrame,
) -> list[str]:

    selected = (
        _first_attr(
            session,
            [
                "selected_columns",
                "confirmed_columns",
                "phase2_selected_columns",
            ],
        )
    )

    # IMPORTANT:
    # Never silently fall back to all dataset columns.
    if not isinstance(
        selected,
        (
            list,
            tuple,
        ),
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 2 selected columns "
                "are not available. "
                "Complete Phase 2 before "
                "opening Phase 6."
            ),
        )

    columns = list(
        dict.fromkeys(
            str(item)
            for item in selected
            if str(item) in df.columns
        )
    )

    if not columns:

        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 2 contains no valid "
                "selected columns for Phase 6."
            ),
        )

    return columns


# ============================================================
# PHASE 5 RECOMMENDATIONS
# ============================================================

def _recommendations(
    session: Any,
) -> list[
    dict[str, Any]
]:

    value = (
        _first_attr(
            session,
            [
                "phase5_recommendations",
                "recommendations",
                "model_recommendations",
                "phase5_result",
                "phase5_response",
            ],
        )
    )

    if isinstance(
        value,
        dict,
    ):

        value = (
            value.get(
                "recommendations"
            )
            or
            value.get(
                "recommended_models"
            )
            or
            value.get(
                "models"
            )
            or
            value.get(
                "result"
            )
            or
            []
        )

        if isinstance(
            value,
            dict,
        ):

            value = (
                value.get(
                    "recommendations"
                )
                or
                value.get(
                    "recommended_models"
                )
                or
                value.get(
                    "models"
                )
                or
                []
            )

    result: list[
        dict[str, Any]
    ] = []

    for item in (
        value
        if isinstance(
            value,
            list,
        )
        else []
    ):

        if isinstance(
            item,
            str,
        ):

            result.append(
                {
                    "model": item,
                    "model_full_name":
                        _full_model_name(item),
                }
            )

        elif isinstance(
            item,
            dict,
        ):

            copied = dict(
                item
            )

            model = (
                copied.get(
                    "model"
                )
                or
                copied.get(
                    "name"
                )
                or
                copied.get(
                    "model_name"
                )
            )

            if model:

                copied[
                    "model_full_name"
                ] = _full_model_name(
                    model
                )

            result.append(
                copied
            )

    return result


def _recommendation_top_three(
    session: Any,
) -> list[
    dict[str, Any]
]:

    return (
        _recommendations(
            session
        )[:3]
    )


# ============================================================
# PHASE 4 OBJECTIVE
# ============================================================

def _objective(
    session: Any,
) -> dict[str, Any]:

    value = (
        _first_attr(
            session,
            [
                "phase4_objective",
                "objective_understanding",
                "objective_validation",
                "phase4_result",
            ],
        )
    )

    if isinstance(value, dict):
        nested = value.get("objective")
        if isinstance(nested, dict):
            return nested
        return value

    return {}


# ============================================================
# JOURNEY
# ============================================================

def _summary(
    session: Any,
) -> Any:

    return _first_attr(
        session,
        [
            "summary",
            "phase1_summary",
            "dataset_summary",
        ],
    )


def _statistical_result(
    session: Any,
) -> Any:

    return _first_attr(
        session,
        [
            "statistical_result",
            "phase3_statistics",
            "analysis",
        ],
    )


def _journey(
    session: Any,
    selected: list[str],
    recommendations: list[
        dict[str, Any]
    ],
    objective: dict[str, Any],
) -> dict[str, Any]:

    return {

        "phase1_dataset_overview":
            _summary(
                session
            ),

        "phase2_selected_columns":
            selected,

        "phase3_statistical_analysis":
            _statistical_result(
                session
            ),

        "phase3_preprocessing":
            _phase3_preprocessing_metadata(
                session
            ),

        "phase4_objective_understanding":
            objective,

        "phase5_model_recommendations":
            recommendations,
    }


# ============================================================
# RESULT CONSISTENCY / MODEL CONTRACT
# ============================================================

def _enrich_model_contract(
    result: dict[str, Any],
    target_columns: list[str],
    explain_by_columns: list[str],
    recommendations: list[dict[str, Any]],
    approach: str,
) -> dict[str, Any]:
    """
    Build the backend source-of-truth contract for Phase 6.

    The detection engine performs the actual PyOD training and
    detection. This function only exposes the values returned by
    that process to the frontend, anomaly detail, and report layers.

    No user-entered expected anomaly percentage is accepted or
    calculated here.
    """

    actual_model = (
        result.get("actual_model")
        or result.get("trained_model")
        or result.get("selected_model")
        or result.get("model")
    )

    actual_model_full_name = (
        result.get("actual_model_full_name")
        or result.get("trained_model_full_name")
        or result.get("selected_model_full_name")
        or _full_model_name(actual_model)
    )

    selected_models = result.get("selected_models") or []
    if not isinstance(selected_models, list):
        selected_models = [selected_models] if selected_models else []

    selected_models = [
        str(model)
        for model in selected_models
        if str(model).strip()
    ]

    if not selected_models and actual_model:
        selected_models = [str(actual_model)]

    selected_model_full_names = (
        result.get("selected_model_full_names") or []
    )
    if not isinstance(selected_model_full_names, list):
        selected_model_full_names = []

    if not selected_model_full_names:
        selected_model_full_names = [
            _full_model_name(model)
            for model in selected_models
        ]

    recommended_models = []
    for item in recommendations:
        if not isinstance(item, dict):
            continue

        model = (
            item.get("model")
            or item.get("name")
            or item.get("model_name")
        )
        if model:
            recommended_models.append(str(model))

    recommended_model = (
        recommended_models[0]
        if recommended_models
        else None
    )

    approach_text = str(approach or "").strip().lower()

    if approach_text in {
        "combined",
        "combined score",
        "combined_score",
    }:
        selected_models = (
            result.get("selected_models")
            or recommended_models[:3]
            or selected_models
        )
        selected_models = list(
            dict.fromkeys(
                str(model)
                for model in selected_models
                if str(model).strip()
            )
        )
        approach_label = "Combined Score"
    else:
        if not selected_models:
            selected_models = (
                [recommended_model]
                if recommended_model
                else []
            )

        if recommended_model:
            selected_models = [recommended_model]

        approach_label = "Best Score"

    if not selected_model_full_names or len(selected_model_full_names) != len(selected_models):
        selected_model_full_names = [
            _full_model_name(model)
            for model in selected_models
        ]

    model_consistency = {
        "recommended_model": recommended_model,
        "recommended_model_full_name":
            _full_model_name(recommended_model),
        "selected_models": selected_models,
        "selected_model_full_names":
            selected_model_full_names,
        "actual_trained_model": actual_model,
        "actual_trained_model_full_name":
            actual_model_full_name,
        "matches_phase5_recommendation": (
            bool(
                selected_models
                and recommended_models
                and all(
                    model in recommended_models
                    for model in selected_models
                )
            )
            if selected_models
            else None
        ),
    }

    # Preserve operational training/detection metadata returned by
    # the detection engine. Contamination is now an explicit Phase 6
    # configuration value and the engine remains the source of truth
    # for the fitted PyOD contamination and resulting labels.
    training_status = result.get("training_status")
    detection_status = result.get("detection_status")

    result["model_training_contract"] = {
        "recommended_model": recommended_model,
        "recommended_model_full_name":
            _full_model_name(recommended_model),
        "selected_models": selected_models,
        "selected_model_full_names":
            selected_model_full_names,
        "actual_trained_model": actual_model,
        "actual_trained_model_full_name":
            actual_model_full_name,
        "pyod_module":
            result.get("pyod_module"),
        "pyod_class":
            result.get("pyod_class"),
        "training_status": training_status,
        "detection_status": detection_status,
        "training_library": "PyOD"
            if (
                result.get("pyod_module")
                or result.get("pyod_class")
            )
            else None,
        "approach": approach_label,
        "target_columns": target_columns,
        "explain_by_columns": explain_by_columns,
        "model_consistency": model_consistency,
    }

    result["actual_model_full_name"] = actual_model_full_name

    if selected_models:
        result["selected_models"] = selected_models
        result["selected_model_full_names"] = (
            selected_model_full_names
        )

    if result.get("pyod_class"):
        result["pyod_class"] = result["pyod_class"]

    if result.get("pyod_module"):
        result["pyod_module"] = result["pyod_module"]

    if training_status:
        result["training_status"] = training_status

    if detection_status:
        result["detection_status"] = detection_status

    result["phase6_backend_source_of_truth"] = {
        "models": selected_models,
        "model_full_names": selected_model_full_names,
        "actual_trained_model": actual_model,
        "model_full_name": actual_model_full_name,
        "target_columns": target_columns,
        "explain_by_columns": explain_by_columns,
        "records": len(result.get("records") or []),
        "anomaly_rate": result.get("anomaly_rate"),
        "contamination": result.get("contamination"),
        "configured_contamination": result.get("configured_contamination"),
        "contamination_mode": result.get("contamination_mode"),
        "pyod_contamination":
            result.get("pyod_contamination"),
    }

    return result


# ============================================================
# DYNAMIC MIN / MAX VALUE EVIDENCE
# ============================================================

def _range_evidence_for_records(
    df: pd.DataFrame,
    records: list[dict[str, Any]],
    target_columns: list[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """
    Calculate a deterministic 0-100 value-position for every target
    column in every returned record using that column's dataset minimum
    and maximum.

    Formula for numeric data:
        ((actual - minimum) / (maximum - minimum)) * 100

    Minimum = 0 percent.
    Maximum = 100 percent.

    This is a value-position indicator for the user interface. It is
    deliberately separate from the PyOD anomaly score and does not alter
    anomaly labels or thresholds.
    """
    statistics: dict[str, dict[str, Any]] = {}

    for column in target_columns:
        if column not in df.columns:
            continue

        series = df[column]

        if pd.api.types.is_bool_dtype(series):
            values = series.astype("Int64").astype(float).dropna()
            if len(values):
                statistics[column] = {
                    "type": "numeric",
                    "minimum": float(values.min()),
                    "maximum": float(values.max()),
                }
            continue

        if pd.api.types.is_numeric_dtype(series):
            values = pd.to_numeric(series, errors="coerce").dropna()
            if len(values):
                statistics[column] = {
                    "type": "numeric",
                    "minimum": float(values.min()),
                    "maximum": float(values.max()),
                }
            continue

        if _looks_like_datetime(series):
            values = pd.to_datetime(series, errors="coerce", utc=True).dropna()
            if len(values):
                statistics[column] = {
                    "type": "datetime",
                    "minimum": values.min().isoformat(),
                    "maximum": values.max().isoformat(),
                }

    def json_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value) if np.isfinite(value) else None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        return value

    def position(actual: Any, stats: dict[str, Any]) -> float | None:
        if stats["type"] == "numeric":
            value = pd.to_numeric(pd.Series([actual]), errors="coerce").iloc[0]
            if pd.isna(value):
                return None
            low = float(stats["minimum"])
            high = float(stats["maximum"])
            if not np.isfinite(low) or not np.isfinite(high):
                return None
            if abs(high - low) <= 1e-12:
                return 100.0
            return float(np.clip((float(value) - low) / (high - low) * 100.0, 0.0, 100.0))

        parsed = pd.to_datetime(pd.Series([actual]), errors="coerce", utc=True).iloc[0]
        if pd.isna(parsed):
            return None
        low = pd.to_datetime(stats["minimum"], errors="coerce", utc=True)
        high = pd.to_datetime(stats["maximum"], errors="coerce", utc=True)
        if pd.isna(low) or pd.isna(high):
            return None
        low_ns = float(low.value)
        high_ns = float(high.value)
        if abs(high_ns - low_ns) <= 1e-12:
            return 100.0
        return float(np.clip((float(parsed.value) - low_ns) / (high_ns - low_ns) * 100.0, 0.0, 100.0))

    for index, record in enumerate(records):
        evidence: list[dict[str, Any]] = []
        if index >= len(df):
            record["range_evidence"] = evidence
            continue

        row = df.iloc[index]
        for column in target_columns:
            stats = statistics.get(column)
            if not stats:
                continue

            actual = row.get(column)
            bar = position(actual, stats)
            if bar is None:
                continue

            evidence.append({
                "column": column,
                "label": str(column).replace("_", " ").title(),
                "actual_value": json_value(actual),
                "minimum": json_value(stats["minimum"]),
                "maximum": json_value(stats["maximum"]),
                "range_position_percent": round(bar, 2),
                "bar_percent": round(bar, 2),
                "value_type": stats["type"],
                "formula": "(actual - minimum) / (maximum - minimum) * 100",
                "source": "dataset_min_max",
            })

        record["range_evidence"] = evidence

    return records, statistics


# ============================================================
# PHASE 6 CONFIG
# ============================================================

@router.get(
    "/{dataset_id}/config"
)
async def get_phase6_config(
    dataset_id: str,
):

    session = (
        _get_session(
            dataset_id
        )
    )

    df = (
        _load_dataframe(
            session
        )
    )

    # Keep the original uploaded dataframe only for report lineage.
    # Detection continues to use the exact Phase 3 dataframe above.
    original_df = _load_original_dataframe(session)

    selected = (
        _phase2_selected_columns(
            session,
            df,
        )
    )

    recommendations = (
        _recommendation_top_three(
            session
        )
    )

    objective = (
        _objective(
            session
        )
    )

    # Phase 4 semantic target suggestions are
    # informational only.
    semantic_targets: list[str] = []

    for item in (
        objective.get(
            "target_columns"
        )
        or []
    ):

        if isinstance(
            item,
            dict,
        ):

            column = (
                item.get(
                    "column"
                )
                or
                item.get(
                    "name"
                )
            )

        else:

            column = item

        if (
            column in selected
            and
            column not in semantic_targets
        ):

            semantic_targets.append(
                column
            )

    return {

        "dataset_id":
            dataset_id,

        # Phase 2 is the maximum allowed pool.
        "selected_columns":
            selected,

        "available_target_columns":
            selected,

        "available_explain_by_columns":
            selected,

        # User chooses these in Phase 6.
        "target_columns":
            [],

        "explain_by_columns":
            [],

        # Informational only.
        "suggested_target_columns":
            semantic_targets,

        "records":
            int(
                len(df)
            ),

        "recommendations":
            recommendations,

        "objective":
            objective,

        "selection_rule":
            (
                "Phase 2 selected columns form "
                "the maximum Phase 6 column pool. "
                "Phase 4 semantic suggestions are "
                "informational only. Phase 6 Target "
                "and Explain By selections are "
                "controlled by the investigator."
            ),

        "model_selection_rule":
            (
                "Phase 5 recommendations are the only "
                "model source. Best Score uses the top Phase 5 "
                "recommendation; Combined Score uses the top "
                "three Phase 5 recommendations. The actual "
                "trained PyOD model(s) and native thresholds "
                "returned by the backend are the source of truth."
            ),
    }


# ============================================================
# TRAIN + DETECT
# ============================================================

@router.post(
    "/{dataset_id}/detect",
    response_model=Phase6Response,
)
async def detect_phase6(
    dataset_id: str,
    request: DetectionRequest,
):

    session = (
        _get_session(
            dataset_id
        )
    )

    df = (
        _load_dataframe(
            session
        )
    )

    # Original dataframe is required later for report lineage only.
    # Phase 6 detection continues to use the Phase 3 dataframe above.
    original_df = (
        _load_original_dataframe(
            session
        )
    )

    selected = (
        _phase2_selected_columns(
            session,
            df,
        )
    )

    # --------------------------------------------------------
    # Target columns are mandatory.
    # --------------------------------------------------------

    if not request.target_columns:

        raise HTTPException(
            status_code=400,
            detail=(
                "Select at least one "
                "Target / Detection Column."
            ),
        )

    target_columns = list(
        dict.fromkeys(
            str(column)
            for column in
            request.target_columns
        )
    )

    explain_by_columns = list(
        dict.fromkeys(
            str(column)
            for column in
            (
                request.explain_by_columns
                or []
            )
        )
    )

    # --------------------------------------------------------
    # STRICT PHASE 2 VALIDATION
    # --------------------------------------------------------

    invalid_target = [
        column
        for column in target_columns
        if column not in selected
    ]

    invalid_explain = [
        column
        for column in explain_by_columns
        if column not in selected
    ]

    if invalid_target:

        raise HTTPException(
            status_code=400,
            detail=(
                "Target Columns must come "
                "only from Phase 2 selected "
                "columns: "
                +
                ", ".join(
                    invalid_target
                )
            ),
        )

    if invalid_explain:

        raise HTTPException(
            status_code=400,
            detail=(
                "Explain By Columns must come "
                "only from Phase 2 selected "
                "columns: "
                +
                ", ".join(
                    invalid_explain
                )
            ),
        )

    # A column can be both a target and Explain By
    # only if the frontend explicitly requests it.
    # We preserve the investigator's selection rather
    # than silently changing it.

    recommendations = (
        _recommendation_top_three(
            session
        )
    )

    objective = (
        _objective(
            session
        )
    )

    # Resolve the explicit UI choice once at the API boundary.
    # Default PyOD is deliberately represented as 0.10 rather than
    # relying on an implicit library default.
    effective_contamination = (
        0.10
        if request.contamination_mode == "default"
        else float(request.contamination)
    )

    try:

        result = (
            run_detection(
                df[selected].copy(),
                target_columns=target_columns,
                explain_by_columns=explain_by_columns,
                approach=request.approach,
                contamination=effective_contamination,
                recommendations=recommendations,
                phase4_objective=objective,
            )
        )

    except (
        ValueError,
        RuntimeError,
        ImportError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            ),
        ) from exc

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "Phase 6 detection engine "
                "did not return a valid result."
            ),
        )

    result["contamination_mode"] = request.contamination_mode
    result["configured_contamination"] = effective_contamination
    result["configured_contamination_percentage"] = effective_contamination * 100.0

    # Make Phase 3 data lineage explicit in the result.
    # The dataframe passed to run_detection() is the same dataframe
    # used for Phase 6 records and explanations.
    preprocessing_source = "unknown"

    for name in (
        "preprocessed_df",
        "processed_df",
        "preprocessed_data",
        "processed_data",
    ):
        value = _first_attr(session, [name])
        candidate = _as_dataframe(value)

        if candidate is not None and not candidate.empty:
            preprocessing_source = name
            break

    if preprocessing_source == "unknown":
        for result_name in (
            "preprocess_result",
            "phase3_preprocess_result",
            "preprocessing_result",
            "phase3_result",
        ):
            value = _first_attr(session, [result_name])
            if not isinstance(value, dict):
                continue

            for key in (
                "preprocessed_df",
                "processed_df",
                "preprocessed_data",
                "processed_data",
                "dataframe",
                "df",
                "data",
            ):
                candidate = _as_dataframe(value.get(key))
                if candidate is not None and not candidate.empty:
                    preprocessing_source = f"{result_name}.{key}"
                    break

            if preprocessing_source != "unknown":
                break

    result["phase3_data_source"] = preprocessing_source
    result["preprocessing_used"] = preprocessing_source != "unknown"

    # --------------------------------------------------------
    # Normalize actual record status.
    #
    # The detection engine is responsible for assigning the
    # actual anomaly status. We do not infer anomalies here.
    # --------------------------------------------------------

    records = result.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):

        records = []

    result[
        "records"
    ] = records

    # --------------------------------------------------------
    # Dynamic min/max value-position evidence.
    # This is calculated from the same Phase 3 dataframe passed to
    # the detection engine. It never changes PyOD classification.
    # --------------------------------------------------------

    try:
        records, range_statistics = _range_evidence_for_records(
            df=df,
            records=records,
            target_columns=target_columns,
        )
        result["records"] = records
        result["range_evidence_configuration"] = {
            "columns": target_columns,
            "statistics": range_statistics,
            "formula": "(actual - minimum) / (maximum - minimum) * 100",
            "minimum_position_percent": 0.0,
            "maximum_position_percent": 100.0,
            "source": "same Phase 3 dataframe used by Phase 6 detection",
            "ui_rule": "The explanation bar width equals the selected record's position between that column's minimum and maximum.",
            "classification_rule": "This value-position indicator does not determine anomaly status; PyOD score and threshold remain authoritative.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to calculate dynamic min/max feature evidence: {exc}",
        ) from exc

    # --------------------------------------------------------
    # Full Phase 1 -> Phase 5 journey.
    # --------------------------------------------------------

    result[
        "journey"
    ] = _journey(
        session=
            session,

        selected=
            selected,

        recommendations=
            recommendations,

        objective=
            objective,
    )

    # --------------------------------------------------------
    # Explicit Phase 6 contract.
    # --------------------------------------------------------

    investigation_columns = list(
        dict.fromkeys(
            target_columns
            +
            explain_by_columns
        )
    )

    result[
        "phase6_contract"
    ] = {

        "phase2_column_pool":
            selected,

        "target_columns":
            target_columns,

        "explain_by_columns":
            explain_by_columns,

        "investigation_columns":
            investigation_columns,

        "filters_allowed_on":
            investigation_columns,

        "visualization_allowed_on":
            investigation_columns,

        "visualization_records":
            "all",

        "anomaly_visualization_rule":
            (
                "Use the actual backend record status. "
                "Only records whose status is Anomaly "
                "are anomalies."
            ),

        "target_visualization_rule":
            (
                "Visualization uses the selected "
                "Target columns and Explain By columns "
                "from Phase 6 only."
            ),
    }

    # --------------------------------------------------------
    # Model / training contract.
    # --------------------------------------------------------

    result = _enrich_model_contract(
        result=
            result,

        target_columns=
            target_columns,

        explain_by_columns=
            explain_by_columns,

        recommendations=
            recommendations,

        approach=
            request.approach,

    )

    # --------------------------------------------------------
    # Detection summary normalization.
    #
    # We preserve values calculated by the detection engine.
    # These are NOT recomputed using fake or independent
    # heuristics.
    # --------------------------------------------------------

    records = result.get(
        "records"
    ) or []

    total_records = len(
        records
    )

    anomaly_records = [
        record
        for record in records
        if str(
            record.get(
                "status"
            )
            or ""
        ).strip().lower()
        == "anomaly"
    ]

    normal_records = [
        record
        for record in records
        if str(
            record.get(
                "status"
            )
            or ""
        ).strip().lower()
        == "normal"
    ]

    anomaly_count = (
        result.get(
            "anomaly_count"
        )
    )

    if anomaly_count is None:
        anomaly_count = len(
            anomaly_records
        )

    normal_count = (
        result.get(
            "normal_count"
        )
    )

    if normal_count is None:
        normal_count = len(
            normal_records
        )

    anomaly_rate = (
        result.get(
            "anomaly_rate"
        )
    )

    if anomaly_rate is None:

        anomaly_rate = (
            float(anomaly_count)
            /
            float(total_records)
            if total_records
            else 0.0
        )

    result[
        "detection_summary"
    ] = {

        "total_records":
            int(
                total_records
            ),

        "anomalies":
            int(
                anomaly_count
            ),

        "normal":
            int(
                normal_count
            ),

        "anomaly_rate":
            float(
                anomaly_rate
            ),

        "contamination":
            result.get("contamination"),

        "contamination_percentage":
            result.get("contamination_percentage"),

        "pyod_contamination":
            result.get("pyod_contamination"),

        "threshold":
            result.get(
                "threshold"
            ),

        "threshold_source":
            result.get(
                "threshold_source"
            )
            or
            "Calculated by the Phase 6 detection engine.",
    }

    # --------------------------------------------------------
    # Report lineage metadata.
    # --------------------------------------------------------
    # These values are captured once from the existing Phase 1/3 data and
    # stored with the Phase 6 result. The PDF generator only presents them;
    # it does not perform a second detection or invent report values.
    preprocessing_meta = _phase3_preprocessing_metadata(session)

    if original_df is not None:
        report_original_columns = [str(column) for column in original_df.columns]
        report_original_record_count = int(len(original_df))
        selected_for_report = [
            column for column in selected if column in original_df.columns
        ]
        before_missing = original_df[selected_for_report].isna().sum().to_dict()
        before_duplicate_records = int(original_df.duplicated().sum())
    else:
        report_original_columns = [str(column) for column in df.columns]
        report_original_record_count = int(len(df))
        selected_for_report = [
            column for column in selected if column in df.columns
        ]
        before_missing = df[selected_for_report].isna().sum().to_dict()
        before_duplicate_records = int(df.duplicated().sum())

    after_missing = df[selected_for_report].isna().sum().to_dict()
    after_duplicate_records = int(df.duplicated().sum())

    # If Phase 3 already provides column-level methods/counts, preserve those
    # exact records. Otherwise create a factual count-only representation.
    stored_columns = []
    if isinstance(preprocessing_meta, dict):
        stored_columns = (
            preprocessing_meta.get("columns")
            or preprocessing_meta.get("column_summary")
            or preprocessing_meta.get("missing_value_handling")
            or []
        )

    report_preprocessing_columns = []
    for item in stored_columns if isinstance(stored_columns, list) else []:
        if isinstance(item, dict):
            report_preprocessing_columns.append(dict(item))

    stored_by_column = {}
    for item in report_preprocessing_columns:
        name = item.get("column") or item.get("name")
        if name:
            stored_by_column[str(name)] = item

    # Ensure every selected column is represented in the report table.
    for column in selected_for_report:
        item = dict(stored_by_column.get(column, {}))
        item["column"] = column
        item.setdefault("before_missing", int(before_missing.get(column, 0)))
        item.setdefault("after_missing", int(after_missing.get(column, 0)))
        item.setdefault("duplicate_before", before_duplicate_records)
        item.setdefault("duplicate_after", after_duplicate_records)
        report_preprocessing_columns.append(item)

    # De-duplicate column entries while preserving Phase 3 order.
    deduped_preprocessing_columns = []
    seen_preprocessing_columns = set()
    for item in report_preprocessing_columns:
        column = str(item.get("column") or item.get("name") or "")
        if not column or column in seen_preprocessing_columns:
            continue
        seen_preprocessing_columns.add(column)
        deduped_preprocessing_columns.append(item)

    result["preprocessing"] = preprocessing_meta
    result["report_metadata"] = {
        "original_columns": report_original_columns,
        "original_record_count": report_original_record_count,
        "phase2_selected_columns": selected_for_report,
        "preprocessing_columns": deduped_preprocessing_columns,
        "duplicate_records_before": before_duplicate_records,
        "duplicate_records_after": after_duplicate_records,
        "preprocessing_source": result.get("phase3_data_source"),
        "source": "Phase 1/Phase 3 stored framework data and the exact dataframe used by Phase 6",
    }

    # --------------------------------------------------------
    # Store result.
    # --------------------------------------------------------

    try:

        _set_attr(
            session,
            "phase6_result",
            result,
        )

        _set_attr(
            session,
            "phase6_completed",
            True,
        )

        _set_attr(
            session,
            "phase6_target_columns",
            target_columns,
        )

        _set_attr(
            session,
            "phase6_explain_by_columns",
            explain_by_columns,
        )

        _set_attr(
            session,
            "phase6_approach",
            request.approach,
        )


        # Store the actual trained model separately as well,
        # when returned by the detection engine.
        actual_model = (
            result.get(
                "actual_model"
            )
            or
            result.get(
                "trained_model"
            )
            or
            result.get(
                "selected_model"
            )
        )

        if actual_model:
            _set_attr(
                session,
                "phase6_actual_model",
                actual_model,
            )

        _set_attr(
            session,
            "phase6_model_training_contract",
            result.get(
                "model_training_contract"
            )
            or {},
        )

    except Exception:
        # Preserve existing store behavior.
        # Detection itself has already completed successfully.
        pass

    return {

        "dataset_id":
            dataset_id,

        "status":
            "completed",

        "result":
            result,
    }


# ============================================================
# GET RESULT
# ============================================================

@router.get(
    "/{dataset_id}/result"
)
async def get_phase6_result(
    dataset_id: str,
):

    session = (
        _get_session(
            dataset_id
        )
    )

    result = (
        _first_attr(
            session,
            [
                "phase6_result"
            ],
        )
    )

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Phase 6 detection has "
                "not been completed."
            ),
        )

    return {

        "dataset_id":
            dataset_id,

        "status":
            "completed",

        "result":
            result,
    }


# ============================================================
# FILTER HELPERS
# ============================================================

def _allowed_columns_from_result(
    result: dict[str, Any],
) -> list[str]:

    contract = (
        result.get(
            "phase6_contract"
        )
        or {}
    )

    allowed = (
        contract.get(
            "investigation_columns"
        )
        or
        result.get(
            "investigation_columns"
        )
        or
        []
    )

    return list(
        dict.fromkeys(
            str(c)
            for c in allowed
        )
    )


def _record_matches_search(
    record: dict[str, Any],
    search: str,
    allowed: list[str],
) -> bool:

    query = (
        str(
            search or ""
        )
        .strip()
        .lower()
    )

    if not query:
        return True

    searchable = [

        record.get(
            "record_index"
        ),

        record.get(
            "status"
        ),

        record.get(
            "anomaly_score"
        ),
    ]

    searchable.extend(

        record.get(
            column
        )

        for column
        in allowed
    )

    return any(

        query
        in
        str(value).lower()

        for value in searchable

        if value is not None
    )


def _number(
    value: Any,
) -> float | None:

    try:

        value = float(
            value
        )

        if np.isfinite(
            value
        ):

            return value

    except (
        TypeError,
        ValueError,
    ):
        pass

    return None


# ============================================================
# SINGLE FILTER
# ============================================================

def _apply_one_filter(
    record: dict[str, Any],
    column: str,
    condition: Any,
) -> bool:

    value = record.get(
        column
    )

    # --------------------------------------------------------
    # Structured filter
    # --------------------------------------------------------

    if isinstance(
        condition,
        dict,
    ):

        # Numeric
        if (
            "min"
            in condition
            or
            "max"
            in condition
        ):

            number = _number(
                value
            )

            if number is None:
                return False

            minimum = _number(
                condition.get(
                    "min"
                )
            )

            maximum = _number(
                condition.get(
                    "max"
                )
            )

            if (
                minimum is not None
                and
                number < minimum
            ):

                return False

            if (
                maximum is not None
                and
                number > maximum
            ):

                return False

        # ----------------------------------------------------
        # Datetime
        # ----------------------------------------------------

        if (
            "from"
            in condition
            or
            "to"
            in condition
        ):

            parsed = pd.to_datetime(
                value,
                errors="coerce",
                utc=True,
            )

            if pd.isna(
                parsed
            ):

                return False

            start = pd.to_datetime(
                condition.get(
                    "from"
                ),
                errors="coerce",
                utc=True,
            )

            end = pd.to_datetime(
                condition.get(
                    "to"
                ),
                errors="coerce",
                utc=True,
            )

            if (
                not pd.isna(start)
                and
                parsed < start
            ):

                return False

            if (
                not pd.isna(end)
                and
                parsed > end
            ):

                return False

        # ----------------------------------------------------
        # Text
        # ----------------------------------------------------

        if (
            "search"
            in condition
        ):

            query = (
                str(
                    condition.get(
                        "search"
                    )
                    or ""
                )
                .strip()
                .lower()
            )

            if (
                query
                and
                query
                not in str(
                    value
                ).lower()
            ):

                return False

        # ----------------------------------------------------
        # Categorical values
        # ----------------------------------------------------

        if (
            "values"
            in condition
        ):

            values = (
                condition.get(
                    "values"
                )
                or []
            )

            allowed_values = {
                str(item)
                for item in values
            }

            if (
                str(value)
                not in allowed_values
            ):

                return False

        return True

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    if isinstance(
        condition,
        list,
    ):

        return (
            str(value)
            in
            {
                str(item)
                for item in condition
            }
        )

    # --------------------------------------------------------
    # Boolean
    # --------------------------------------------------------

    if isinstance(
        condition,
        bool,
    ):

        if isinstance(
            value,
            bool,
        ):

            return (
                value
                is
                condition
            )

        return (
            str(value).lower()
            ==
            str(condition).lower()
        )

    # --------------------------------------------------------
    # Empty
    # --------------------------------------------------------

    if (
        condition is None
        or
        condition == ""
    ):

        return True

    # --------------------------------------------------------
    # Exact value
    # --------------------------------------------------------

    return (
        str(condition).lower()
        ==
        str(value).lower()
    )


# ============================================================
# SORT
# ============================================================

def _sort_records(
    records: list[
        dict[str, Any]
    ],
    sort_by: str,
    direction: str,
) -> list[
    dict[str, Any]
]:

    if not records:
        return records

    reverse = (
        direction
        == "desc"
    )

    def key(
        record: dict[str, Any]
    ):

        value = record.get(
            sort_by
        )

        number = _number(
            value
        )

        if number is not None:

            return (
                0,
                number,
            )

        return (
            1,
            str(
                value or ""
            ).lower(),
        )

    return sorted(
        records,
        key=key,
        reverse=reverse,
    )


# ============================================================
# FILTER RESULTS
# ============================================================

@router.post(
    "/{dataset_id}/filter"
)
async def filter_phase6_results(
    dataset_id: str,
    request: FilterRequest,
):

    session = (
        _get_session(
            dataset_id
        )
    )

    result = (
        _first_attr(
            session,
            [
                "phase6_result"
            ],
        )
    )

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Run Phase 6 detection first."
            ),
        )

    allowed = (
        _allowed_columns_from_result(
            result
        )
    )

    records = list(
        result.get(
            "records"
        )
        or []
    )

    # --------------------------------------------------------
    # Strict investigation filter rule.
    # --------------------------------------------------------

    invalid_filters = [

        column

        for column
        in request.filters.keys()

        if column
        not in allowed
    ]

    if invalid_filters:

        raise HTTPException(
            status_code=400,
            detail=(
                "Investigation filters may use "
                "only Target + Explain By columns: "
                +
                ", ".join(
                    invalid_filters
                )
            ),
        )

    # --------------------------------------------------------
    # Search + filters
    # --------------------------------------------------------

    filtered = [

        record

        for record
        in records

        if _record_matches_search(
            record,
            request.search,
            allowed,
        )

        and

        all(

            _apply_one_filter(
                record,
                column,
                condition,
            )

            for column,
            condition
            in
            request.filters.items()
        )
    ]

    # --------------------------------------------------------
    # Sorting
    # --------------------------------------------------------

    filtered = (
        _sort_records(
            filtered,
            request.sort_by,
            request.sort_direction,
        )
    )

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    total = len(
        filtered
    )

    start = (
        (
            request.page
            - 1
        )
        *
        request.page_size
    )

    end = (
        start
        +
        request.page_size
    )

    return {

        "dataset_id":
            dataset_id,

        "status":
            "completed",

        "allowed_columns":
            allowed,

        "filter_schema":
            result.get(
                "filter_schema"
            )
            or [],

        "total":
            total,

        "page":
            request.page,

        "page_size":
            request.page_size,

        "records":
            filtered[
                start:end
            ],
    }


# ============================================================
# RECORD DETAIL
# ============================================================

@router.get(
    "/{dataset_id}/detail"
)
async def get_phase6_anomaly_detail(
    dataset_id: str,

    record_index: str = Query(
        ...,
        description=(
            "Record index returned by "
            "the Phase 6 anomaly table."
        ),
    ),
):

    session = (
        _get_session(
            dataset_id
        )
    )

    result = (
        _first_attr(
            session,
            [
                "phase6_result"
            ],
        )
    )

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Run Phase 6 detection first."
            ),
        )

    for record in (
        result.get(
            "records"
        )
        or []
    ):

        if (
            str(
                record.get(
                    "record_index"
                )
            )
            ==
            str(
                record_index
            )
        ):

            return {

                "dataset_id":
                    dataset_id,

                "status":
                    "completed",

                "record":
                    record,

                "allowed_columns":
                    _allowed_columns_from_result(
                        result
                    ),

                "target_columns":
                    result.get(
                        "target_columns"
                    )
                    or
                    (
                        result.get(
                            "phase6_contract"
                        )
                        or {}
                    ).get(
                        "target_columns"
                    )
                    or [],

                "explain_by_columns":
                    result.get(
                        "explain_by_columns"
                    )
                    or
                    (
                        result.get(
                            "phase6_contract"
                        )
                        or {}
                    ).get(
                        "explain_by_columns"
                    )
                    or [],

                "model_training_contract":
                    result.get(
                        "model_training_contract"
                    )
                    or {},
            }

    raise HTTPException(
        status_code=404,
        detail=(
            "The requested record "
            "was not found."
        ),
    )


# ============================================================
# RECORD DETAIL PATH COMPATIBILITY
# ============================================================

@router.get(
    "/{dataset_id}/anomaly/{record_index}"
)
async def get_phase6_anomaly_detail_alias(
    dataset_id: str,
    record_index: str,
):

    return await get_phase6_anomaly_detail(
        dataset_id=dataset_id,
        record_index=record_index,
    )


# ============================================================
# VISUALIZATION HELPERS
# ============================================================

def _visualization_data(
    result: dict[str, Any],
    records: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    spec = (
        result.get(
            "visualization"
        )
        or {}
    )

    chart_type = (
        spec.get(
            "type"
        )
    )

    # ========================================================
    # TIME SERIES
    # ========================================================

    if (
        chart_type
        ==
        "time_anomaly"
    ):

        x = (
            spec.get(
                "x_column"
            )
        )

        y = (
            spec.get(
                "y_column"
            )
        )

        points = []

        for record in records:

            parsed = pd.to_datetime(
                record.get(
                    x
                ),
                errors="coerce",
                utc=True,
            )

            number = _number(
                record.get(
                    y
                )
            )

            if (
                pd.isna(
                    parsed
                )
                or
                number is None
            ):

                continue

            points.append(
                {

                    "record_index":
                        record.get(
                            "record_index"
                        ),

                    "x":
                        parsed.isoformat(),

                    "y":
                        number,

                    "anomaly_score":
                        record.get(
                            "anomaly_score"
                        ),

                    # IMPORTANT:
                    # Actual backend status.
                    "status":
                        record.get(
                            "status"
                        ),
                }
            )

        return {

            "type":
                chart_type,

            "spec":
                spec,

            "data":
                points,

            "record_count":
                len(points),

            "anomaly_count":
                sum(
                    str(
                        item.get(
                            "status"
                        )
                        or ""
                    ).lower()
                    == "anomaly"
                    for item in points
                ),
        }

    # ========================================================
    # SCATTER
    # ========================================================

    if (
        chart_type
        ==
        "scatter"
    ):

        x = (
            spec.get(
                "x_column"
            )
        )

        y = (
            spec.get(
                "y_column"
            )
        )

        points = []

        for record in records:

            xv = _number(
                record.get(
                    x
                )
            )

            yv = _number(
                record.get(
                    y
                )
            )

            if (
                xv is None
                or
                yv is None
            ):

                continue

            points.append(
                {

                    "record_index":
                        record.get(
                            "record_index"
                        ),

                    "x":
                        xv,

                    "y":
                        yv,

                    "anomaly_score":
                        record.get(
                            "anomaly_score"
                        ),

                    "status":
                        record.get(
                            "status"
                        ),
                }
            )

        return {

            "type":
                chart_type,

            "spec":
                spec,

            "data":
                points,

            "record_count":
                len(points),

            "anomaly_count":
                sum(
                    str(
                        item.get(
                            "status"
                        )
                        or ""
                    ).lower()
                    == "anomaly"
                    for item in points
                ),
        }

    # ========================================================
    # SCORE VS FEATURE
    # ========================================================

    if (
        chart_type
        ==
        "score_vs_feature"
    ):

        x = (
            spec.get(
                "x_column"
            )
        )

        points = []

        for record in records:

            xv = _number(
                record.get(
                    x
                )
            )

            score = _number(
                record.get(
                    "anomaly_score"
                )
            )

            if (
                xv is None
                or
                score is None
            ):

                continue

            points.append(
                {

                    "record_index":
                        record.get(
                            "record_index"
                        ),

                    "x":
                        xv,

                    "y":
                        score,

                    "anomaly_score":
                        score,

                    "status":
                        record.get(
                            "status"
                        ),
                }
            )

        return {

            "type":
                chart_type,

            "spec":
                spec,

            "data":
                points,

            "record_count":
                len(points),

            "anomaly_count":
                sum(
                    str(
                        item.get(
                            "status"
                        )
                        or ""
                    ).lower()
                    == "anomaly"
                    for item in points
                ),
        }

    # ========================================================
    # CATEGORY ANOMALY RATE
    # ========================================================

    if (
        chart_type
        ==
        "category_anomaly_rate"
    ):

        column = (
            spec.get(
                "x_column"
            )
        )

        groups: dict[
            str,
            dict[str, int]
        ] = {}

        for record in records:

            category = str(
                record.get(
                    column,
                    "<missing>",
                )
            )

            bucket = (
                groups.setdefault(
                    category,
                    {
                        "total":
                            0,

                        "anomalies":
                            0,
                    },
                )
            )

            bucket[
                "total"
            ] += 1

            # Only actual backend anomaly status
            # increments the anomaly count.
            if (
                str(
                    record.get(
                        "status"
                    )
                    or ""
                ).strip().lower()
                ==
                "anomaly"
            ):

                bucket[
                    "anomalies"
                ] += 1

        data = [

            {

                "category":
                    category,

                "total":
                    values[
                        "total"
                    ],

                "anomalies":
                    values[
                        "anomalies"
                    ],

                "anomaly_rate":
                    (
                        values[
                            "anomalies"
                        ]
                        /
                        values[
                            "total"
                        ]
                    )
                    if
                    values[
                        "total"
                    ]
                    else 0.0,
            }

            for category,
            values
            in groups.items()
        ]

        data.sort(
            key=lambda item:
                item[
                    "anomaly_rate"
                ],
            reverse=True,
        )

        return {

            "type":
                chart_type,

            "spec":
                spec,

            "data":
                data,

            "record_count":
                len(records),

            "anomaly_count":
                sum(
                    item[
                        "anomalies"
                    ]
                    for item
                    in data
                ),
        }

    # ========================================================
    # PCA
    # ========================================================

    if (
        chart_type
        ==
        "pca"
    ):

        target_columns = (
            result.get(
                "target_columns"
            )
            or
            (
                result.get(
                    "phase6_contract"
                )
                or {}
            ).get(
                "target_columns"
            )
            or []
        )

        numeric_columns = []

        for column in (
            target_columns
        ):

            numeric_values = [

                _number(
                    record.get(
                        column
                    )
                )

                for record
                in records
            ]

            valid_count = sum(

                value is not None

                for value
                in numeric_values
            )

            if valid_count >= 2:

                numeric_columns.append(
                    column
                )

        if len(
            numeric_columns
        ) >= 3:

            from sklearn.decomposition import PCA

            from sklearn.preprocessing import (
                StandardScaler,
            )

            matrix = []

            for record in records:

                row_values = []

                for column in (
                    numeric_columns
                ):

                    number = _number(
                        record.get(
                            column
                        )
                    )

                    row_values.append(
                        0.0
                        if number is None
                        else number
                    )

                matrix.append(
                    row_values
                )

            matrix = np.asarray(
                matrix,
                dtype=float,
            )

            if len(
                matrix
            ) >= 2:

                scaled = (
                    StandardScaler()
                    .fit_transform(
                        matrix
                    )
                )

                components = (
                    PCA(
                        n_components=2,
                        random_state=42,
                    )
                    .fit_transform(
                        scaled
                    )
                )

                data = [

                    {

                        "record_index":
                            records[i].get(
                                "record_index"
                            ),

                        "x":
                            float(
                                components[
                                    i,
                                    0
                                ]
                            ),

                        "y":
                            float(
                                components[
                                    i,
                                    1
                                ]
                            ),

                        "anomaly_score":
                            records[i].get(
                                "anomaly_score"
                            ),

                        "status":
                            records[i].get(
                                "status"
                            ),
                    }

                    for i in range(
                        len(records)
                    )
                ]

                return {

                    "type":
                        chart_type,

                    "spec":
                        spec,

                    "data":
                        data,

                    "source_columns":
                        numeric_columns,

                    "record_count":
                        len(data),

                    "anomaly_count":
                        sum(
                            str(
                                item.get(
                                    "status"
                                )
                                or ""
                            ).lower()
                            == "anomaly"
                            for item
                            in data
                        ),
                }

    # ========================================================
    # FALLBACK
    # ========================================================

    points = [

        {

            "record_index":
                record.get(
                    "record_index"
                ),

            "x":
                index,

            "y":
                record.get(
                    "anomaly_score"
                ),

            "anomaly_score":
                record.get(
                    "anomaly_score"
                ),

            "status":
                record.get(
                    "status"
                ),
        }

        for index,
        record
        in enumerate(
            records
        )
    ]

    return {

        "type":
            "score_vs_record",

        "spec":
            spec,

        "data":
            points,

        "record_count":
            len(points),

        "anomaly_count":
            sum(
                str(
                    item.get(
                        "status"
                    )
                    or ""
                ).lower()
                == "anomaly"
                for item
                in points
            ),
    }


# ============================================================
# VISUALIZATION API
# ============================================================

@router.get(
    "/{dataset_id}/visualization"
)
async def get_phase6_visualization(
    dataset_id: str,

    search: str = "",

    record_index: str | None = None,
):

    session = (
        _get_session(
            dataset_id
        )
    )

    result = (
        _first_attr(
            session,
            [
                "phase6_result"
            ],
        )
    )

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Run Phase 6 detection first."
            ),
        )

    allowed = (
        _allowed_columns_from_result(
            result
        )
    )

    # IMPORTANT:
    # Start from ALL detected records.
    # No arbitrary 300-record slicing here.
    records = list(
        result.get(
            "records"
        )
        or []
    )

    # --------------------------------------------------------
    # Visualization search is restricted to
    # investigation columns + record metadata.
    # --------------------------------------------------------

    if search.strip():

        records = [

            record

            for record
            in records

            if _record_matches_search(
                record,
                search,
                allowed,
            )
        ]

    if (
        record_index is not None
        and
        str(
            record_index
        ).strip()
    ):

        records = [

            record

            for record
            in records

            if (
                str(
                    record.get(
                        "record_index"
                    )
                )
                ==
                str(
                    record_index
                )
            )
        ]

    visualization = (
        _visualization_data(
            result,
            records,
        )
    )

    return {

        "dataset_id":
            dataset_id,

        "status":
            "completed",

        "allowed_columns":
            allowed,

        "target_columns":
            result.get(
                "target_columns"
            )
            or
            (
                result.get(
                    "phase6_contract"
                )
                or {}
            ).get(
                "target_columns"
            )
            or [],

        "explain_by_columns":
            result.get(
                "explain_by_columns"
            )
            or
            (
                result.get(
                    "phase6_contract"
                )
                or {}
            ).get(
                "explain_by_columns"
            )
            or [],

        "total_detected_records":
            len(
                result.get(
                    "records"
                )
                or []
            ),

        "visualization":
            visualization,
    }


# ============================================================
# VISUALIZATION POST COMPATIBILITY
# ============================================================

@router.post(
    "/{dataset_id}/visualization"
)
async def post_phase6_visualization(
    dataset_id: str,
    payload: dict[str, Any] | None = None,
):

    """
    POST compatibility endpoint for frontend clients that send
    visualization filters in the request body.

    The detection result is never retrained or modified here.
    """

    payload = payload or {}

    search = str(
        payload.get(
            "search"
        )
        or ""
    )

    filters = (
        payload.get(
            "filters"
        )
        or {}
    )

    if (
        not search
        and
        isinstance(
            filters,
            dict,
        )
    ):

        search = str(
            filters.get(
                "search"
            )
            or ""
        )

    session = _get_session(
        dataset_id
    )

    result = _first_attr(
        session,
        [
            "phase6_result"
        ],
    )

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Run Phase 6 detection first."
            ),
        )

    allowed = (
        _allowed_columns_from_result(
            result
        )
    )

    records = list(
        result.get(
            "records"
        )
        or []
    )

    if search.strip():

        records = [

            record

            for record
            in records

            if _record_matches_search(
                record,
                search,
                allowed,
            )
        ]

    record_index = (
        payload.get(
            "record_index"
        )
    )

    if (
        record_index is None
        and
        isinstance(
            filters,
            dict,
        )
    ):

        record_index = (
            filters.get(
                "record_index"
            )
        )

    if (
        record_index is not None
        and
        str(
            record_index
        ).strip()
    ):

        records = [

            record

            for record
            in records

            if (
                str(
                    record.get(
                        "record_index"
                    )
                )
                ==
                str(
                    record_index
                )
            )
        ]

    visualization = (
        _visualization_data(
            result,
            records,
        )
    )

    return {

        "dataset_id":
            dataset_id,

        "status":
            "completed",

        "allowed_columns":
            allowed,

        "target_columns":
            result.get(
                "target_columns"
            )
            or
            (
                result.get(
                    "phase6_contract"
                )
                or {}
            ).get(
                "target_columns"
            )
            or [],

        "explain_by_columns":
            result.get(
                "explain_by_columns"
            )
            or
            (
                result.get(
                    "phase6_contract"
                )
                or {}
            ).get(
                "explain_by_columns"
            )
            or [],

        "visualization":
            visualization,
    }


# ============================================================
# PDF REPORT
# ============================================================

@router.get(
    "/{dataset_id}/report"
)
async def download_phase6_report(
    dataset_id: str,
):

    session = (
        _get_session(
            dataset_id
        )
    )

    result = (
        _first_attr(
            session,
            [
                "phase6_result"
            ],
        )
    )

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Run Phase 6 detection first."
            ),
        )

    # The report receives the exact Phase 6 result stored
    # after detection. No second model run occurs here.
    try:

        pdf_bytes = (
            generate_report(
                result,
                dataset_id,
            )
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(
                exc
            ),
        ) from exc

    return StreamingResponse(

        BytesIO(
            pdf_bytes
        ),

        media_type=
            "application/pdf",

        headers={

            "Content-Disposition":
                (
                    'attachment; '
                    'filename='
                    '"ANOMALY_Phase6_Report.pdf"'
                )
        },
    )