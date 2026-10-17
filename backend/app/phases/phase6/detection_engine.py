from __future__ import annotations 

import importlib
import inspect
import logging
import random 
from dataclasses import dataclass 
from typing import Any 

import numpy as np 
import pandas as pd 

from sklearn.preprocessing import RobustScaler 

from .explainability import explain_record 


logger = logging.getLogger(__name__)

# ============================================================ 
# MODEL ALIASES 
# ============================================================ 

MODEL_ALIASES = { 

    "ecod": 
        "ECOD", 

    "empirical cumulative distribution-based outlier detection": 
        "ECOD", 

    "empirical cumulative distribution-based outlier detection (ecod)": 
        "ECOD", 

    "isolation forest": 
        "IForest", 

    "isolation forest (iforest)": 
        "IForest", 

    "iforest": 
        "IForest", 

    "copod": 
        "COPOD", 

    "copula-based outlier detection": 
        "COPOD", 

    "copula-based outlier detection (copod)": 
        "COPOD", 

    "knn": 
        "KNN", 

    "k-nearest neighbors": 
        "KNN", 

    "k-nearest neighbors (knn)": 
        "KNN", 

    "lof": 
        "LOF", 

    "local outlier factor": 
        "LOF", 

    "local outlier factor (lof)": 
        "LOF", 

    "cblof": 
        "CBLOF", 

    "cluster-based local outlier factor": 
        "CBLOF", 

    "cluster-based local outlier factor (cblof)": 
        "CBLOF", 

    "hbos": 
        "HBOS", 

    "histogram-based outlier score": 
        "HBOS", 

    "histogram-based outlier score (hbos)": 
        "HBOS", 

    "matrixprofile": 
        "MatrixProfile", 

    "matrix profile": 
        "MatrixProfile", 

    "spectralresidual": 
        "SpectralResidual", 

    "spectral residual": 
        "SpectralResidual", 

    "kshape": 
        "KShape", 

    "k-shape": 
        "KShape", 
} 


# ============================================================ 
# FULL PROFESSIONAL MODEL NAMES 
# ============================================================ 

DISPLAY_NAMES = { 

    "ECOD": 
        ( 
            "Empirical Cumulative " 
            "Distribution-based Outlier " 
            "Detection (ECOD)" 
        ), 

    "IForest": 
        "Isolation Forest (IForest)", 

    "COPOD": 
        ( 
            "Copula-Based Outlier " 
            "Detection (COPOD)" 
        ), 

    "KNN": 
        "K-Nearest Neighbors (KNN)", 

    "LOF": 
        "Local Outlier Factor (LOF)", 

    "CBLOF": 
        ( 
            "Cluster-Based Local " 
            "Outlier Factor (CBLOF)" 
        ), 

    "HBOS": 
        ( 
            "Histogram-Based Outlier " 
            "Score (HBOS)" 
        ), 

    "MatrixProfile": 
        "Matrix Profile", 

    "SpectralResidual": 
        "Spectral Residual", 

    "KShape": 
        "K-Shape", 
} 


# ============================================================ 
# SUPPORTED MODELS 
# ============================================================ 

SUPPORTED_MODELS = { 
    "ECOD", 
    "IForest", 
    "COPOD", 
    "KNN", 
    "LOF", 
    "CBLOF", 
    "HBOS", 
    "MatrixProfile", 
    "SpectralResidual", 
    "KShape", 
}

# Fixed seed used to make stochastic detector training reproducible.
DETERMINISTIC_RANDOM_STATE = 42 


# ============================================================ 
# FEATURE MATRIX 
# ============================================================ 

@dataclass 
class FeatureMatrix: 

    X: np.ndarray 

    feature_names: list[str] 

    feature_sources: list[str] 

    source_types: dict[str, str] 


# ============================================================ 
# JSON CONVERSION 
# ============================================================ 

def _json_value( 
    value: Any, 
) -> Any: 

    if value is None: 
        return None 

    if isinstance( 
        value, 
        np.integer, 
    ): 

        return int(value) 

    if isinstance( 
        value, 
        np.floating, 
    ): 

        return ( 
            float(value) 
            if np.isfinite(value) 
            else None 
        ) 

    if isinstance( 
        value, 
        pd.Timestamp, 
    ): 

        return value.isoformat() 

    if isinstance( 
        value, 
        np.bool_, 
    ): 

        return bool(value) 

    if isinstance( 
        value, 
        ( 
            bool, 
            int, 
            float, 
            str, 
        ), 
    ): 

        return value 

    try: 

        if pd.isna(value): 
            return None 

    except Exception: 
        pass 

    return str(value) 


# ============================================================ 
# MODEL NAME NORMALIZATION 
# ============================================================ 

def _model_key( 
    value: Any, 
) -> str: 

    text = str( 
        value or "" 
    ).strip().lower() 

    return MODEL_ALIASES.get( 
        text, 
        str( 
            value or "" 
        ).strip(), 
    ) 


# ============================================================ 
# RECOMMENDATIONS 
# ============================================================ 

def _recommendation_items( 
    recommendations: Any, 
) -> list[dict[str, Any]]: 

    if isinstance( 
        recommendations, 
        dict, 
    ): 

        recommendations = ( 
            recommendations.get( 
                "recommendations" 
            ) 
            or 
            recommendations.get( 
                "recommended_models" 
            ) 
            or 
            recommendations.get( 
                "models" 
            ) 
            or [] 
        ) 

    result: list[dict[str, Any]] = [] 

    for item in ( 
        recommendations or [] 
    ): 

        if isinstance( 
            item, 
            str, 
        ): 

            result.append( 
                { 
                    "model": 
                        item, 

                    "final_score": 
                        None, 
                } 
            ) 

        elif isinstance( 
            item, 
            dict, 
        ): 

            result.append( 
                item 
            ) 

    return result 


def _extract_model_name( 
    item: dict[str, Any], 
) -> str: 

    return _model_key( 

        item.get( 
            "model" 
        ) 

        or 

        item.get( 
            "display_name" 
        ) 

        or 

        item.get( 
            "name" 
        ) 

        or 

        item.get( 
            "model_name" 
        ) 
    ) 


# ============================================================ 
# DATA TYPE HELPERS 
# ============================================================ 

def _numeric_series( 
    series: pd.Series, 
) -> pd.Series: 

    return pd.to_numeric( 
        series, 
        errors="coerce", 
    ) 


def _looks_like_datetime( 
    series: pd.Series, 
) -> bool: 

    if pd.api.types.is_datetime64_any_dtype( 
        series 
    ): 
        return True 

    if pd.api.types.is_numeric_dtype( 
        series 
    ): 
        return False 

    non_null = ( 
        series.dropna() 
    ) 

    if len(non_null) < 5: 
        return False 

    parsed = pd.to_datetime( 
        non_null.astype(str), 
        errors="coerce", 
        utc=True, 
    ) 

    return ( 
        float( 
            parsed.notna().mean() 
        ) 
        >= 0.80 
    ) 


def _safe_string( 
    series: pd.Series, 
) -> pd.Series: 

    return ( 
        series 
        .astype("string") 
        .fillna("<missing>") 
    ) 


# ============================================================ 
# FEATURE BLOCK 
# ============================================================ 

def _add_scaled( 
    blocks: list[np.ndarray], 
    names: list[str], 
    sources: list[str], 
    source: str, 
    block: np.ndarray, 
    feature_names: list[str], 
) -> None: 

    block = np.asarray( 
        block, 
        dtype=float, 
    ) 

    if block.ndim == 1: 

        block = ( 
            block.reshape( 
                -1, 
                1, 
            ) 
        ) 

    for j in range( 
        block.shape[1] 
    ): 

        values = block[:, j] 

        values = np.nan_to_num( 
            values, 
            nan=0.0, 
            posinf=0.0, 
            neginf=0.0, 
        ) 

        if ( 
            float( 
                np.nanstd(values) 
            ) 
            <= 1e-12 
        ): 
            continue 

        blocks.append( 
            values.reshape( 
                -1, 
                1, 
            ) 
        ) 

        names.append( 
            feature_names[j] 
        ) 

        sources.append( 
            source 
        ) 


# ============================================================ 
# BUILD DETECTION FEATURES 
# ============================================================ 

def _build_features( 
    df: pd.DataFrame, 
    target_columns: list[str], 
) -> FeatureMatrix: 

    """ 
    Detection features come ONLY from Target / Detection Columns. 

    Explain By Columns are NOT silently injected into the model. 
    They remain available for investigation and explanation. 
    """ 

    target_columns = [ 
        c 
        for c in target_columns 
        if c in df.columns 
    ] 

    if not target_columns: 

        raise ValueError( 
            "Select at least one " 
            "Target / Detection Column." 
        ) 

    blocks: list[np.ndarray] = [] 

    names: list[str] = [] 

    sources: list[str] = [] 

    source_types: dict[str, str] = {} 

    for column in target_columns: 

        series = df[column] 

        # ---------------------------------------------------- 
        # BOOLEAN 
        # ---------------------------------------------------- 

        if pd.api.types.is_bool_dtype( 
            series 
        ): 

            source_types[ 
                column 
            ] = "boolean" 

            values = ( 
                series 
                .astype("boolean") 
                .fillna(False) 
                .astype(int) 
                .to_numpy( 
                    dtype=float 
                ) 
            ) 

            _add_scaled( 
                blocks, 
                names, 
                sources, 
                column, 
                RobustScaler() 
                .fit_transform( 
                    values.reshape( 
                        -1, 
                        1, 
                    ) 
                ), 
                [ 
                    f"{column}::boolean" 
                ], 
            ) 

            continue 

        # ---------------------------------------------------- 
        # NUMERIC 
        # ---------------------------------------------------- 

        if pd.api.types.is_numeric_dtype( 
            series 
        ): 

            source_types[ 
                column 
            ] = "numeric" 

            values = ( 
                _numeric_series( 
                    series 
                ) 
            ) 

            median = ( 
                float( 
                    values.median() 
                ) 
                if values.notna().any() 
                else 0.0 
            ) 

            values = ( 
                values 
                .fillna(median) 
                .to_numpy( 
                    dtype=float 
                ) 
            ) 

            _add_scaled( 
                blocks, 
                names, 
                sources, 
                column, 
                RobustScaler() 
                .fit_transform( 
                    values.reshape( 
                        -1, 
                        1, 
                    ) 
                ), 
                [ 
                    f"{column}::value" 
                ], 
            ) 

            continue 

        # ---------------------------------------------------- 
        # DATETIME 
        # ---------------------------------------------------- 

        if _looks_like_datetime( 
            series 
        ): 

            source_types[ 
                column 
            ] = "datetime" 

            parsed = pd.to_datetime( 
                series, 
                errors="coerce", 
                utc=True, 
            ) 

            fallback = ( 

                parsed 
                .dropna() 
                .median() 

                if parsed.notna().any() 

                else 
                pd.Timestamp( 
                    "1970-01-01", 
                    tz="UTC", 
                ) 
            ) 

            parsed = ( 
                parsed.fillna( 
                    fallback 
                ) 
            ) 

            seconds = ( 
                parsed 
                .astype("int64") 
                .to_numpy( 
                    dtype=float 
                ) 
                / 1e9 
            ) 

            dt = parsed.dt 

            month = ( 
                dt.month 
                .to_numpy( 
                    dtype=float 
                ) 
            ) 

            dow = ( 
                dt.dayofweek 
                .to_numpy( 
                    dtype=float 
                ) 
            ) 

            hour = ( 
                dt.hour 
                .to_numpy( 
                    dtype=float 
                ) 
            ) 

            date_block = ( 
                np.column_stack( 
                    [ 
                        seconds, 

                        np.sin( 
                            2 
                            * np.pi 
                            * month 
                            / 12.0 
                        ), 

                        np.cos( 
                            2 
                            * np.pi 
                            * month 
                            / 12.0 
                        ), 

                        np.sin( 
                            2 
                            * np.pi 
                            * dow 
                            / 7.0 
                        ), 

                        np.cos( 
                            2 
                            * np.pi 
                            * dow 
                            / 7.0 
                        ), 

                        np.sin( 
                            2 
                            * np.pi 
                            * hour 
                            / 24.0 
                        ), 

                        np.cos( 
                            2 
                            * np.pi 
                            * hour 
                            / 24.0 
                        ), 
                    ] 
                ) 
            ) 

            scaled = ( 
                RobustScaler() 
                .fit_transform( 
                    date_block 
                ) 
            ) 

            _add_scaled( 
                blocks, 
                names, 
                sources, 
                column, 
                scaled, 
                [ 
                    f"{column}::timestamp", 
                    f"{column}::month_sin", 
                    f"{column}::month_cos", 
                    f"{column}::dow_sin", 
                    f"{column}::dow_cos", 
                    f"{column}::hour_sin", 
                    f"{column}::hour_cos", 
                ], 
            ) 

            continue 

        # ---------------------------------------------------- 
        # CATEGORICAL / TEXT 
        # ---------------------------------------------------- 

        source_types[ 
            column 
        ] = "categorical_or_text" 

        text = _safe_string( 
            series 
        ) 

        unique_count = int( 
            text.nunique( 
                dropna=False 
            ) 
        ) 

        ratio = ( 
            unique_count 
            / 
            max( 
                len(df), 
                1, 
            ) 
        ) 

        # Small categorical domain 
        if ( 
            unique_count <= 50 
            and ratio <= 0.20 
        ): 

            dummies = ( 
                pd.get_dummies( 
                    text, 
                    prefix=column, 
                    dtype=float, 
                ) 
            ) 

            _add_scaled( 
                blocks, 
                names, 
                sources, 
                column, 
                dummies.to_numpy( 
                    dtype=float 
                ), 
                [ 
                    f"{column}::{c}" 
                    for c in dummies.columns 
                ], 
            ) 

        # High-cardinality text / identifier 
        else: 

            counts = ( 
                text.value_counts( 
                    dropna=False 
                ) 
            ) 

            frequency = ( 
                text.map( 
                    counts 
                ) 
                .to_numpy( 
                    dtype=float 
                ) 
                / 
                max( 
                    len(df), 
                    1, 
                ) 
            ) 

            lengths = ( 
                text.str.len() 
                .to_numpy( 
                    dtype=float 
                ) 
            ) 

            max_len = max( 
                float( 
                    np.nanmax( 
                        lengths 
                    ) 
                ) 
                if len(lengths) 
                else 1.0, 
                1.0, 
            ) 

            text_block = ( 
                np.column_stack( 
                    [ 
                        frequency, 
                        lengths / max_len, 
                    ] 
                ) 
            ) 

            _add_scaled( 
                blocks, 
                names, 
                sources, 
                column, 
                RobustScaler() 
                .fit_transform( 
                    text_block 
                ), 
                [ 
                    f"{column}::frequency", 
                    f"{column}::length", 
                ], 
            ) 

    if not blocks: 

        raise ValueError( 
            "The selected detection columns " 
            "do not contain enough usable variation " 
            "for anomaly detection." 
        ) 

    X = np.hstack( 
        blocks 
    ) 

    X = np.nan_to_num( 
        X, 
        nan=0.0, 
        posinf=0.0, 
        neginf=0.0, 
    ) 

    return FeatureMatrix( 
        X=X, 
        feature_names=names, 
        feature_sources=sources, 
        source_types=source_types, 
    ) 


# ============================================================ 
# PYOD MODEL IMPORT 
# ============================================================ 

def _import_model_class( 
    model_name: str, 
): 

    module_map = { 

        "ECOD": 
            ( 
                "pyod.models.ecod", 
                "ECOD", 
            ), 

        "IForest": 
            ( 
                "pyod.models.iforest", 
                "IForest", 
            ), 

        "COPOD": 
            ( 
                "pyod.models.copod", 
                "COPOD", 
            ), 

        "KNN": 
            ( 
                "pyod.models.knn", 
                "KNN", 
            ), 

        "LOF": 
            ( 
                "pyod.models.lof", 
                "LOF", 
            ), 

        "CBLOF": 
            ( 
                "pyod.models.cblof", 
                "CBLOF", 
            ), 

        "HBOS": 
            ( 
                "pyod.models.hbos", 
                "HBOS", 
            ), 

        "MatrixProfile": 
            ( 
                "pyod.models.ts_matrix_profile", 
                "MatrixProfile", 
            ), 

        "KShape": 
            ( 
                "pyod.models.ts_kshape", 
                "KShape", 
            ), 
    } 

    # SpectralResidual availability differs 
    # between PyOD versions. 
    if model_name == "SpectralResidual": 

        candidates = [ 

            ( 
                "pyod.models.sr", 
                "SpectralResidual", 
            ), 

            ( 
                "pyod.models.ts_spectral_residual", 
                "SpectralResidual", 
            ), 
        ] 

    else: 

        if model_name not in module_map: 

            raise ImportError( 
                f"Unknown PyOD model " 
                f"'{model_name}'." 
            ) 

        candidates = [ 
            module_map[ 
                model_name 
            ] 
        ] 

    last_error: Exception | None = None 

    for ( 
        module_name, 
        class_name, 
    ) in candidates: 

        try: 

            module = ( 
                importlib.import_module( 
                    module_name 
                ) 
            ) 

            cls = getattr( 
                module, 
                class_name, 
            ) 

            # ------------------------------------------------ 
            # HARD VERIFICATION: 
            # The instantiated class must actually come 
            # from PyOD. 
            # ------------------------------------------------ 

            if not str( 
                getattr( 
                    cls, 
                    "__module__", 
                    "", 
                ) 
            ).startswith( 
                "pyod." 
            ): 

                raise ImportError( 
                    f"Resolved class " 
                    f"'{class_name}' is not " 
                    f"a PyOD class." 
                ) 

            return cls 

        except Exception as exc: 

            last_error = exc 

    raise ImportError( 
        f"PyOD model " 
        f"'{model_name}' " 
        "is unavailable in the " 
        "installed PyOD version." 
    ) from last_error 


# ============================================================ 
# MODEL CREATION 
# ============================================================ 

def _make_model(
    model_name: str,
    n_rows: int,
    contamination: float,
):
    """Create exactly the PyOD detector selected by Phase 5.

    CBLOF is configured explicitly and deterministically. No constructor
    fallback is used because changing model parameters after a failure can
    make the actual detector configuration unclear.
    """
    model_name = _model_key(model_name)
    cls = _import_model_class(model_name)
    n_neighbors = min(20, max(2, n_rows - 1))

    if model_name == "KNN":
        kwargs = {"n_neighbors": n_neighbors}
    elif model_name == "LOF":
        kwargs = {"n_neighbors": n_neighbors}
    elif model_name == "CBLOF":
        kwargs = {
            "n_clusters": min(8, max(2, n_rows - 1)),
            "alpha": 0.9,
            "beta": 5,
            "random_state": DETERMINISTIC_RANDOM_STATE,
        }
    elif model_name == "HBOS":
        kwargs = {}
    elif model_name == "MatrixProfile":
        kwargs = {}
    elif model_name == "KShape":
        kwargs = {}
    else:
        kwargs = {}

    # Pass the resolved Phase 6 contamination explicitly to PyOD.
    # This prevents an implicit library default from controlling the
    # fitted threshold and keeps custom contamination meaningful.
    try:
        signature = inspect.signature(cls)
        accepts_contamination = (
            "contamination" in signature.parameters
            or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
        )
    except (TypeError, ValueError):
        accepts_contamination = False

    if accepts_contamination:
        kwargs["contamination"] = float(contamination)
    elif abs(float(contamination) - 0.10) > 1e-12:
        raise RuntimeError(
            f"The selected PyOD model '{model_name}' does not expose a "
            "contamination parameter, so the requested custom contamination "
            "cannot be applied safely."
        )

    try:
        model = cls(**kwargs)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Unable to instantiate the selected PyOD model '{model_name}' "
            f"with configuration {kwargs}."
        ) from exc

    if not model.__class__.__module__.startswith("pyod."):
        raise RuntimeError("The instantiated anomaly detector is not a PyOD model.")

    return model


def _model_fit_input(
    model_name: str,
    X: np.ndarray,
) -> np.ndarray:
    """
    Adapt the representation required by sequence-oriented PyOD models.
    The selected detection features themselves are not changed.
    """
    X = np.asarray(X, dtype=float)

    if X.ndim != 2:
        X = X.reshape(len(X), -1)

    if model_name == "KShape":
        return X.reshape(X.shape[0], X.shape[1], 1)

    if model_name == "MatrixProfile":
        # Matrix Profile is sequence-oriented.  Use the first selected
        # engineered feature as the sequence when multiple features exist.
        return X[:, 0]

    return X


def _fit_and_score(
    model_name: str,
    X: np.ndarray,
    contamination: float = 0.10,
) -> tuple[
    Any,
    np.ndarray,
    np.ndarray,
    float,
    float | None,
]:
    """Fit the exact selected PyOD model once and return native results.

    PyOD remains the source of truth for decision scores, threshold_ and
    labels_. Repeated runs with identical input/configuration use the same
    random state, including CBLOF's internal clustering initialization.
    """
    model_name = _model_key(model_name)

    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported PyOD model '{model_name}'.")

    try:
        contamination = float(contamination)
    except (TypeError, ValueError) as exc:
        raise ValueError("Contamination must be a numeric value.") from exc

    if not 0.01 <= contamination <= 0.50:
        raise ValueError("Contamination must be between 0.01 and 0.50.")

    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        X = X.reshape(len(X), -1)
    if len(X) < 5:
        raise ValueError("At least 5 records are required for anomaly detection.")

    # Protect stochastic libraries that consult the process-wide RNG.
    random.seed(DETERMINISTIC_RANDOM_STATE)
    np.random.seed(DETERMINISTIC_RANDOM_STATE)

    model = _make_model(
        model_name,
        len(X),
        contamination,
    )
    fit_X = _model_fit_input(model_name, X)

    try:
        model.fit(fit_X)
    except Exception as exc:
        config = {}
        try:
            config = model.get_params(deep=False)
        except Exception:
            pass
        raise RuntimeError(
            f"Unable to train the selected PyOD model '{model_name}'. "
            f"The model was not replaced by another detector. Configuration: {config}"
        ) from exc

    # Compact diagnostics only. Printing one line per record makes large runs
    # dramatically slower and can flood terminal logs. PyOD's native scores,
    # labels and threshold remain unchanged.
    model_contamination = getattr(model, "contamination", None)
    model_threshold = getattr(model, "threshold_", None)
    model_labels = getattr(model, "labels_", None)
    model_scores = getattr(model, "decision_scores_", None)
    if model_scores is not None:
        debug_scores = np.asarray(model_scores, dtype=float).reshape(-1)
        anomaly_count = (
            int((np.asarray(model_labels).reshape(-1) != 0).sum())
            if model_labels is not None
            and len(np.asarray(model_labels).reshape(-1)) == len(debug_scores)
            else None
        )
        logger.debug(
            "Phase 6 fitted model=%s rows=%d contamination=%s threshold=%s anomalies=%s",
            model_name, len(debug_scores), model_contamination, model_threshold, anomaly_count,
        )
    else:
        logger.debug("Phase 6 fitted model=%s; model decision_scores_ unavailable", model_name)

    decision_scores = getattr(model, "decision_scores_", None)
    if decision_scores is not None:
        scores = np.asarray(decision_scores, dtype=float).reshape(-1)
    else:
        scores = np.asarray(model.decision_function(fit_X), dtype=float).reshape(-1)

    if len(scores) != len(X):
        raise RuntimeError(
            f"PyOD model '{model_name}' returned an invalid number of anomaly scores."
        )

    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)

    threshold_value = getattr(model, "threshold_", None)
    if threshold_value is None:
        raise RuntimeError(
            f"PyOD model '{model_name}' did not expose threshold_ after fit()."
        )
    threshold = float(threshold_value)

    labels_value = getattr(model, "labels_", None)
    if labels_value is None:
        labels_value = model.predict(fit_X)
    labels = np.asarray(labels_value, dtype=int).reshape(-1)
    if len(labels) != len(X):
        raise RuntimeError(
            f"PyOD model '{model_name}' returned an invalid number of anomaly labels."
        )
    labels = (labels != 0).astype(int)

    contamination_value = getattr(model, "contamination", None)
    try:
        contamination = float(contamination_value) if contamination_value is not None else None
    except (TypeError, ValueError):
        contamination = None

    return model, scores, labels, threshold, contamination


# ============================================================ 
# SCORE NORMALIZATION 
# ============================================================ 

def _minmax( 
    values: np.ndarray, 
) -> np.ndarray: 

    values = np.asarray( 
        values, 
        dtype=float, 
    ) 

    if len(values) == 0: 

        return np.zeros( 
            0, 
            dtype=float, 
        ) 

    lo = float( 
        np.nanmin(values) 
    ) 

    hi = float( 
        np.nanmax(values) 
    ) 

    if ( 
        not np.isfinite(lo) 
        or 
        not np.isfinite(hi) 
        or 
        hi - lo <= 1e-12 
    ): 

        return np.zeros_like( 
            values, 
            dtype=float, 
        ) 

    return ( 
        values - lo 
    ) / ( 
        hi - lo 
    ) 


# ============================================================ 
# DYNAMIC VISUALIZATION SELECTION 
# ============================================================ 

def _choose_visualization( 
    df: pd.DataFrame, 
    target_columns: list[str], 
    explain_by_columns: list[str], 
) -> dict[str, Any]: 

    investigation_columns = ( 
        list( 
            dict.fromkeys( 
                target_columns 
                + explain_by_columns 
            ) 
        ) 
    ) 

    numeric_targets = [ 

        c 

        for c in target_columns 

        if ( 
            c in df.columns 
            and 
            pd.api.types.is_numeric_dtype( 
                df[c] 
            ) 
        ) 
    ] 

    datetime_columns = [ 

        c 

        for c in investigation_columns 

        if ( 
            c in df.columns 
            and 
            _looks_like_datetime( 
                df[c] 
            ) 
        ) 
    ] 

    categorical_columns = [ 

        c 

        for c in investigation_columns 

        if ( 
            c in df.columns 

            and 
            not pd.api.types.is_numeric_dtype( 
                df[c] 
            ) 

            and 
            not pd.api.types.is_bool_dtype( 
                df[c] 
            ) 

            and 
            not _looks_like_datetime( 
                df[c] 
            ) 
        ) 
    ] 

    if ( 
        datetime_columns 
        and 
        numeric_targets 
    ): 

        return { 
            "type": "time_anomaly", 
            "x_column": datetime_columns[0], 
            "y_column": numeric_targets[0], 
            "available_target_columns": numeric_targets, 
            "available_explain_by_columns": explain_by_columns, 
            "all_records": True, 
            "uses_backend_status": True, 
            "anomaly_visual_style": "anomaly_records_only", 
            "description": "Selected numeric target behavior over time, with backend anomaly status.", 
        } 

    if len(numeric_targets) >= 3: 

        return { 
            "type": "pca", 
            "x_column": "component_1", 
            "y_column": "component_2", 
            "available_target_columns": numeric_targets, 
            "available_explain_by_columns": explain_by_columns, 
            "all_records": True, 
            "uses_backend_status": True, 
            "anomaly_visual_style": "anomaly_records_only", 
            "description": "Two-dimensional projection of the selected numeric detection features. All analyzed records remain available and only backend labelled anomalies are highlighted.", 
        } 

    if len(numeric_targets) >= 2: 

        return { 
            "type": "scatter", 
            "x_column": numeric_targets[0], 
            "y_column": numeric_targets[1], 
            "available_target_columns": numeric_targets, 
            "available_explain_by_columns": explain_by_columns, 
            "all_records": True, 
            "uses_backend_status": True, 
            "anomaly_visual_style": "anomaly_records_only", 
            "description": "Relationship between selected numeric detection features. All analyzed records remain available; only backend anomalies are highlighted.", 
        } 

    if numeric_targets: 

        return { 
            "type": "score_vs_feature", 
            "x_column": numeric_targets[0], 
            "y_column": "anomaly_score", 
            "available_target_columns": numeric_targets, 
            "available_explain_by_columns": explain_by_columns, 
            "all_records": True, 
            "uses_backend_status": True, 
            "anomaly_visual_style": "anomaly_records_only", 
            "description": "Anomaly score compared with the selected numeric detection feature. All records are retained and only actual anomalies are highlighted.", 
        } 

    if categorical_columns: 

        return { 
            "type": "category_anomaly_rate", 
            "x_column": categorical_columns[0], 
            "y_column": "anomaly_rate", 
            "available_target_columns": target_columns, 
            "available_explain_by_columns": explain_by_columns, 
            "all_records": True, 
            "uses_backend_status": True, 
            "anomaly_visual_style": "anomaly_records_only", 
            "description": "Anomaly rate across categories using backend anomaly labels. Explain By columns may provide investigative context but are not silently added to detection.", 
        } 

    return { 
        "type": "score_vs_record", 
        "x_column": "record_index", 
        "y_column": "anomaly_score", 
        "available_target_columns": target_columns, 
        "available_explain_by_columns": explain_by_columns, 
        "all_records": True, 
        "uses_backend_status": True, 
        "anomaly_visual_style": "anomaly_records_only", 
        "description": "Anomaly score by record order because no suitable numeric or categorical visualization dimension was available.", 
    } 


# ============================================================ 
# FILTER SCHEMA 
# ============================================================ 

def _filter_schema( 
    df: pd.DataFrame, 
    allowed_columns: list[str], 
) -> list[dict[str, Any]]: 

    schema: list[dict[str, Any]] = [] 

    for column in allowed_columns: 

        if column not in df.columns: 
            continue 

        series = df[column] 

        if pd.api.types.is_bool_dtype(series): 
            schema.append({ 
                "column": column, 
                "type": "boolean", 
                "values": [True, False], 
            }) 
            continue 

        if pd.api.types.is_numeric_dtype(series): 
            values = _numeric_series(series) 
            if values.notna().any(): 
                schema.append({ 
                    "column": column, 
                    "type": "numeric", 
                    "min": float(values.min()), 
                    "max": float(values.max()), 
                }) 
            continue 

        if _looks_like_datetime(series): 
            parsed = pd.to_datetime(series, errors="coerce", utc=True) 
            if parsed.notna().any(): 
                schema.append({ 
                    "column": column, 
                    "type": "datetime", 
                    "min": parsed.min().isoformat(), 
                    "max": parsed.max().isoformat(), 
                }) 
            continue 

        values = series.dropna().astype(str) 
        unique = values.unique().tolist() 

        if len(unique) <= 50: 
            schema.append({ 
                "column": column, 
                "type": "categorical", 
                "values": unique, 
            }) 
        else: 
            schema.append({ 
                "column": column, 
                "type": "text", 
            }) 

    return schema 


# ============================================================ 
# VISIBLE INVESTIGATION COLUMNS 
# ============================================================ 

def _objective_model_columns(
    phase4_objective: dict[str, Any] | None,
    fallback_target_columns: list[str],
    all_columns: list[str],
) -> list[str]:
    """Return confirmed Phase 4 attributes for the Objective-Based model."""
    objective = phase4_objective if isinstance(phase4_objective, dict) else {}
    understanding = objective.get("objective_understanding")
    if not isinstance(understanding, dict):
        understanding = objective.get("objective")
    if not isinstance(understanding, dict):
        understanding = objective

    candidates = []
    raw_attributes = understanding.get("attributes_involved") or objective.get("attributes_involved") or []
    for item in raw_attributes:
        if isinstance(item, str):
            column, role = item.strip(), ""
        elif isinstance(item, dict):
            column = str(item.get("column") or item.get("name") or item.get("column_name") or item.get("field") or "").strip()
            role = str(item.get("role") or "").strip().lower().replace(" ", "_")
        else:
            continue
        if column in all_columns and role not in {"entity_identifier", "entity"}:
            candidates.append(column)

    for key in ("target_columns", "reference_columns", "context_columns"):
        for item in (understanding.get(key) or objective.get(key) or []):
            if isinstance(item, str):
                column = item.strip()
            elif isinstance(item, dict):
                column = str(item.get("column") or item.get("name") or item.get("column_name") or item.get("field") or "").strip()
            else:
                continue
            if column in all_columns:
                candidates.append(column)

    candidates.extend(c for c in fallback_target_columns if c in all_columns)
    return list(dict.fromkeys(candidates))


def _visible_columns( 
    target_columns: list[str], 
    explain_by_columns: list[str], 
) -> list[str]: 

    return list(dict.fromkeys(target_columns + explain_by_columns)) 


# ============================================================
# DYNAMIC MIN / MAX RANGE EVIDENCE
# ============================================================

def _build_range_statistics(
    df: pd.DataFrame,
    columns: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Build immutable dataset-level minimum and maximum values for
    the selected detection columns.

    These statistics are used only for the Phase 6 explanation bar.
    They do not alter PyOD scores, thresholds, or anomaly labels.
    """
    statistics: dict[str, dict[str, Any]] = {}

    for column in columns:
        if column not in df.columns:
            continue

        series = df[column]

        if pd.api.types.is_bool_dtype(series):
            numeric = series.astype("Int64").astype(float)
            values = numeric.dropna()
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
            parsed = pd.to_datetime(series, errors="coerce", utc=True).dropna()
            if len(parsed):
                statistics[column] = {
                    "type": "datetime",
                    "minimum": parsed.min().isoformat(),
                    "maximum": parsed.max().isoformat(),
                }

    return statistics


def _range_position(
    actual: Any,
    minimum: Any,
    maximum: Any,
    value_type: str,
) -> float | None:
    """Return the actual record position between dataset min and max as 0..100."""
    if value_type == "numeric":
        value = pd.to_numeric(pd.Series([actual]), errors="coerce").iloc[0]
        if pd.isna(value):
            return None
        low = float(minimum)
        high = float(maximum)
        if not np.isfinite(low) or not np.isfinite(high):
            return None
        if abs(high - low) <= 1e-12:
            return 100.0
        return float(np.clip((float(value) - low) / (high - low) * 100.0, 0.0, 100.0))

    if value_type == "datetime":
        parsed = pd.to_datetime(pd.Series([actual]), errors="coerce", utc=True).iloc[0]
        if pd.isna(parsed):
            return None
        low = pd.to_datetime(minimum, utc=True, errors="coerce")
        high = pd.to_datetime(maximum, utc=True, errors="coerce")
        if pd.isna(low) or pd.isna(high):
            return None
        low_ns = float(low.value)
        high_ns = float(high.value)
        if abs(high_ns - low_ns) <= 1e-12:
            return 100.0
        return float(np.clip((float(parsed.value) - low_ns) / (high_ns - low_ns) * 100.0, 0.0, 100.0))

    return None


def _build_record_range_evidence(
    df: pd.DataFrame,
    row_index: int,
    columns: list[str],
    range_statistics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Calculate dynamic value-position evidence for one record.

    For numeric columns:
        position_percent = (actual - minimum) / (maximum - minimum) * 100

    Therefore a value equal to the dataset minimum is 0 percent and a
    value equal to the dataset maximum is 100 percent. The result is
    intentionally a value-position measure, not a fabricated anomaly
    contribution or High/Medium/Low classification.
    """
    if row_index < 0 or row_index >= len(df):
        return []

    row = df.iloc[row_index]
    evidence: list[dict[str, Any]] = []

    for column in columns:
        stats = range_statistics.get(column)
        if not stats:
            continue

        actual = row.get(column)
        position = _range_position(
            actual=actual,
            minimum=stats["minimum"],
            maximum=stats["maximum"],
            value_type=stats["type"],
        )

        if position is None:
            continue

        evidence.append({
            "column": column,
            "label": str(column).replace("_", " ").title(),
            "actual_value": _json_value(actual),
            "minimum": _json_value(stats["minimum"]),
            "maximum": _json_value(stats["maximum"]),
            "range_position_percent": round(float(position), 2),
            "bar_percent": round(float(position), 2),
            "value_type": stats["type"],
            "range_formula": "(actual - minimum) / (maximum - minimum) * 100",
            "evidence_source": "dataset_min_max",
        })

    return evidence


# ============================================================ 
# RECORD PAYLOAD 
# ============================================================ 

def _record_payload( 
    df: pd.DataFrame, 
    scores: np.ndarray, 
    labels: np.ndarray, 
    raw_model_scores: dict[str, np.ndarray], 
    normalized_model_scores: dict[str, np.ndarray], 
    weights: dict[str, float], 
    visible_columns: list[str], 
) -> list[dict[str, Any]]: 

    records: list[dict[str, Any]] = [] 

    for i, (_, row) in enumerate(df.iterrows()): 

        is_anomaly = int(labels[i]) == 1 

        payload: dict[str, Any] = { 
            "record_index": _json_value(df.index[i]), 
            "anomaly_score": float(scores[i]), 
            "status": "Anomaly" if is_anomaly else "Normal", 
            "anomaly_status": "Anomaly" if is_anomaly else "Normal", 
            "is_anomaly": bool(is_anomaly), 
            "prediction": 1 if is_anomaly else 0, 
            "rank": 0, 
        } 

        for column in visible_columns: 
            payload[column] = _json_value(row[column]) 

        model_evidence = [] 

        for name, values in raw_model_scores.items(): 
            model_evidence.append({ 
                "model": name, 
                "display_name": DISPLAY_NAMES.get(name, name), 
                "raw_score": float(values[i]), 
                "normalized_score": float(normalized_model_scores[name][i]), 
                "weight": float(weights.get(name, 0.0)), 
            }) 

        payload["model_evidence"] = model_evidence 
        records.append(payload) 

    order = np.argsort(-scores, kind="mergesort") 

    for rank, idx in enumerate(order, start=1): 
        records[int(idx)]["rank"] = rank 

    return records 


# ============================================================ 
# MAIN DETECTION ENGINE 
# ============================================================ 

def run_detection( 
    df: pd.DataFrame, 
    target_columns: list[str], 
    explain_by_columns: list[str], 
    approach: str, 
    contamination: float = 0.10, 
    recommendations: Any = None, 
    phase4_objective: dict[str, Any] | None = None, 
) -> dict[str, Any]: 

    if len(df) < 5: 
        raise ValueError("At least 5 records are required for anomaly detection.") 

    try:
        contamination = float(contamination)
    except (TypeError, ValueError) as exc:
        raise ValueError("Contamination must be a numeric value between 0.01 and 0.50.") from exc

    if not np.isfinite(contamination) or not 0.01 <= contamination <= 0.50:
        raise ValueError("Contamination must be between 0.01 (1%) and 0.50 (50%).")

    all_columns = list(df.columns) 

    target_columns = list(dict.fromkeys(target_columns)) 
    explain_by_columns = list(dict.fromkeys(explain_by_columns)) 

    invalid_targets = [c for c in target_columns if c not in all_columns] 
    invalid_explain = [c for c in explain_by_columns if c not in all_columns] 

    if invalid_targets: 
        raise ValueError("These detection columns are not present in Phase 2: " + ", ".join(invalid_targets)) 

    if invalid_explain: 
        raise ValueError("These Explain By columns are not present in Phase 2: " + ", ".join(invalid_explain)) 

    if not target_columns: 
        raise ValueError("Select at least one Target / Detection Column.") 

    visible_columns = _visible_columns(target_columns, explain_by_columns) 

    objective_model_columns = _objective_model_columns(
        phase4_objective=phase4_objective,
        fallback_target_columns=target_columns,
        all_columns=all_columns,
    )

    feature_matrix = _build_features(
        df=df,
        target_columns=objective_model_columns,
    )

    logger.debug(
        "Phase 6 objective feature matrix: columns=%s generated_features=%d sources=%s",
        objective_model_columns, feature_matrix.X.shape[1], feature_matrix.feature_sources,
    )

    rec_items = _recommendation_items(recommendations) 

    if not rec_items: 
        raise ValueError("Phase 5 model recommendations are not available. Complete Phase 5 before running detection.") 

    top_three = rec_items[:3] 
    phase5_top_model = _extract_model_name(rec_items[0]) 

    if phase5_top_model not in SUPPORTED_MODELS: 
        raise ValueError(f"Phase 5 returned an unsupported top recommended model: '{phase5_top_model}'.") 

    approach_text = str(approach or "").strip() 
    approach_lower = approach_text.lower() 

    if approach_lower in {"best_score", "best score", "best", "recommended", "recommended_model"}: 
        normalized_approach = "best_score" 
        chosen_items = [rec_items[0]] 
    elif approach_lower in {"combined_score", "combined score", "combined"}: 
        normalized_approach = "combined_score" 
        chosen_items = top_three 
        if len(chosen_items) < 3: 
            raise ValueError("Combined Score requires at least 3 Phase 5 model recommendations.") 
    else: 
        explicit_model = _model_key(approach_text) 
        if explicit_model not in SUPPORTED_MODELS: 
            raise ValueError(f"Unknown Phase 6 approach/model '{approach_text}'.") 
        normalized_approach = "explicit_model" 
        matching_item = next((item for item in rec_items if _extract_model_name(item) == explicit_model), None) 
        if matching_item is None: 
            raise ValueError(f"Model '{explicit_model}' is not present in the Phase 5 recommendations.") 
        chosen_items = [matching_item] 

    requested_model_names: list[str] = [] 

    for item in chosen_items: 
        name = _extract_model_name(item) 
        if name in SUPPORTED_MODELS and name not in requested_model_names: 
            requested_model_names.append(name) 

    if not requested_model_names: 
        raise ValueError("No valid PyOD model was selected for Phase 6.") 

    if normalized_approach == "combined_score" and len(requested_model_names) != 3: 
        raise ValueError("Combined Score requires three distinct supported models from the Phase 5 top three recommendations.") 

    model_objects: dict[str, Any] = {} 
    raw_scores: dict[str, np.ndarray] = {} 
    normalized_scores: dict[str, np.ndarray] = {} 
    native_thresholds: dict[str, float] = {} 
    pyod_contaminations: dict[str, float | None] = {} 
    model_metadata: list[dict[str, Any]] = [] 
    failures: list[dict[str, str]] = [] 

    for item in chosen_items: 
        name = _extract_model_name(item) 

        if not name or name in raw_scores: 
            continue 

        if name not in SUPPORTED_MODELS: 
            failures.append({ 
                "model": name, 
                "display_name": DISPLAY_NAMES.get(name, name), 
                "error": "Model is not in the supported PyOD model list.", 
            }) 
            raise RuntimeError(f"The selected model '{name}' is not a supported PyOD model.") 

        try: 
            model, scores, pyod_labels, native_threshold, pyod_contamination = _fit_and_score( 
                model_name=name, 
                X=feature_matrix.X, 
                contamination=contamination, 
            ) 

            scores = np.asarray(scores, dtype=float).reshape(-1) 

            if len(scores) != len(df): 
                raise ValueError("Model returned an unexpected number of scores.") 

            model_objects[name] = model 
            raw_scores[name] = scores 
            normalized_scores[name] = _minmax(scores) 
            native_thresholds[name] = float(native_threshold) 
            pyod_contaminations[name] = pyod_contamination 

            recommendation_score = item.get("final_score") 
            if recommendation_score is None: 
                recommendation_score = item.get("score") 

            try: 
                recommendation_score = float(recommendation_score) 
            except (TypeError, ValueError): 
                recommendation_score = None 

            model_metadata.append({ 
                "model": name, 
                "display_name": DISPLAY_NAMES.get(name, name), 
                "recommendation_score": recommendation_score, 
                "pyod_contamination": pyod_contamination, 
                "pyod_threshold": float(native_threshold), 
                "score_source": "PyOD decision_scores_ or decision_function()", 
                "fit_status": "completed", 
            }) 

        except Exception as exc: 
            failures.append({ 
                "model": name, 
                "display_name": DISPLAY_NAMES.get(name, name), 
                "error": str(exc), 
            }) 
            raise RuntimeError( 
                f"The selected model '{DISPLAY_NAMES.get(name, name)}' could not be trained. " 
                "Phase 6 did not silently replace it with another recommended model. " 
                f"Backend error: {exc}" 
            ) from exc 

    if not raw_scores: 
        raise RuntimeError("None of the selected Phase 5 models could be trained.") 

    weights: dict[str, float] = {} 

    if normalized_approach == "combined_score" and len(raw_scores) == 3: 
        raw_weight_values: dict[str, float] = {} 

        for meta in model_metadata: 
            score = meta.get("recommendation_score") 
            if meta["model"] in raw_scores: 
                raw_weight_values[meta["model"]] = max(float(score), 0.0) if score is not None else 0.0 

        total = sum(raw_weight_values.values()) 

        if total <= 0: 
            equal = 1.0 / len(raw_weight_values) 
            weights = {name: equal for name in raw_weight_values} 
        else: 
            weights = {name: value / total for name, value in raw_weight_values.items()} 

        combined = np.zeros(len(df), dtype=float) 
        combined_threshold = 0.0 

        for name in requested_model_names: 
            weight = weights.get(name, 0.0) 
            combined += weight * normalized_scores[name] 

            score_min = float(np.nanmin(raw_scores[name])) 
            score_max = float(np.nanmax(raw_scores[name])) 

            if np.isfinite(score_min) and np.isfinite(score_max) and score_max - score_min > 1e-12: 
                normalized_threshold = (native_thresholds[name] - score_min) / (score_max - score_min) 
            else: 
                normalized_threshold = 0.0 

            combined_threshold += weight * float(np.clip(normalized_threshold, 0.0, 1.0)) 

        final_scores = combined 
        threshold = float(combined_threshold) 
        labels = (final_scores > threshold).astype(int) 

        threshold_method = "weighted_combination_of_native_pyod_thresholds" 
        detection_rule = ( 
            "Each selected PyOD model supplies its native anomaly score and fitted threshold. " 
            "Scores and thresholds are normalized into a common range, combined using the Phase 5 " 
            "recommendation weights, and records whose combined score exceeds the combined PyOD-derived " 
            "threshold are labelled Anomaly." 
        ) 

    else: 
        selected_name = requested_model_names[0] 
        final_scores = raw_scores[selected_name] 
        threshold = float(native_thresholds[selected_name]) 

        labels = (final_scores > threshold).astype(int) 

        native_labels = np.asarray( 
            getattr(model_objects[selected_name], "labels_", labels), 
            dtype=int, 
        ).reshape(-1) 

        if len(native_labels) == len(labels): 
            native_labels = (native_labels != 0).astype(int) 
            if not np.array_equal(labels, native_labels): 
                labels = native_labels 

        weights = {selected_name: 1.0} 
        threshold_method = "native_pyod_threshold" 
        detection_rule = ( 
            "The fitted Phase 5 top-ranked PyOD model supplies its native decision scores, threshold_, " 
            "and labels_. The configured Phase 6 contamination value is passed directly to the PyOD " 
            "constructor and therefore controls the fitted native threshold." 
        ) 

    anomaly_count = int(labels.sum()) 
    normal_count = int(len(df) - anomaly_count) 
    anomaly_rate = float((anomaly_count / len(df)) * 100.0) 

    contamination_values = [value for value in pyod_contaminations.values() if value is not None] 

    pyod_contamination = ( 
        float(contamination_values[0]) 
        if contamination_values and all(abs(value - contamination_values[0]) <= 1e-12 for value in contamination_values) 
        else None 
    ) 

    detected_contamination = float(anomaly_count / len(df)) 

    trained_model_names = list(raw_scores.keys()) 

    records = _record_payload( 
        df=df, 
        scores=final_scores, 
        labels=labels, 
        raw_model_scores=raw_scores, 
        normalized_model_scores=normalized_scores, 
        weights=weights, 
        visible_columns=visible_columns, 
    ) 

    # Dataset min/max statistics are calculated once from the same
    # Phase 3 dataframe used for detection. They are used only for
    # the dynamic explanation bars and never modify PyOD results.
    range_columns = list(dict.fromkeys(target_columns))
    range_statistics = _build_range_statistics(
        df=df,
        columns=range_columns,
    )

    for idx in range(len(df)):
        records[idx]["range_evidence"] = _build_record_range_evidence(
            df=df,
            row_index=idx,
            columns=range_columns,
            range_statistics=range_statistics,
        )

    # -------------------------------------------------------- 
    # EXPLANATIONS — EVERY RECORD, NORMAL + ANOMALY 
    # -------------------------------------------------------- 

    explanation_indexes = np.arange(len(df), dtype=int) 

    for idx in explanation_indexes: 

        if normalized_approach == "combined_score" and len(model_objects) > 1: 
            # The explanation card identifies the detection approach as
            # Combined Score, while model_evidence below preserves the
            # actual PyOD detectors used in the ensemble.
            explanation_model_name = "Combined Score"
            model_name = max( 
                weights, 
                key=lambda key: weights.get(key, 0.0), 
            ) 
        else: 
            model_name = next(iter(model_objects))
            explanation_model_name = model_name

        model = model_objects[model_name] 

        model_evidence = [ 
            { 
                "model": name, 
                "display_name": DISPLAY_NAMES.get(name, name), 
                "raw_score": float(raw_scores[name][int(idx)]), 
                "normalized_score": float(normalized_scores[name][int(idx)]), 
                "weight": float(weights.get(name, 0.0)), 
                "pyod_threshold": float(native_thresholds[name]), 
            } 
            for name in raw_scores 
        ] 

        explanation = explain_record( 
            model=model, 
            X=feature_matrix.X, 
            row_index=int(idx), 
            feature_names=feature_matrix.feature_names, 
            feature_sources=feature_matrix.feature_sources, 
            raw_row=df.iloc[int(idx)], 
            reference_df=df, 
            target_columns=objective_model_columns, 
            explain_by_columns=explain_by_columns, 
            model_name=explanation_model_name, 
            anomaly_score=float(final_scores[idx]), 
            threshold=threshold, 
            model_evidence=model_evidence, 
            objective=phase4_objective, 
            record_status=( 
                "Anomaly" 
                if int(labels[idx]) == 1 
                else "Normal" 
            ), 
        ) 

        records[int(idx)]["explanation"] = explanation 

    normalized_weighted = [] 

    for meta in model_metadata: 
        name = meta["model"] 
        normalized_weighted.append({ 
            **meta, 
            "weight": float(weights.get(name, 0.0)), 
        }) 

    actual_trained_model = trained_model_names[0] if len(trained_model_names) == 1 else None 

    actual_trained_model_full_name = ( 
        DISPLAY_NAMES.get(actual_trained_model, actual_trained_model) 
        if actual_trained_model 
        else None 
    ) 

    selected_model = ( 
        requested_model_names[0] 
        if normalized_approach in {"best_score", "explicit_model"} and requested_model_names 
        else None 
    ) 

    selected_model_full_name = ( 
        DISPLAY_NAMES.get(selected_model, selected_model) 
        if selected_model 
        else None 
    ) 

    visualization = _choose_visualization( 
        df=df, 
        target_columns=target_columns, 
        explain_by_columns=explain_by_columns, 
    ) 

    return { 
        "approach": normalized_approach, 
        "approach_requested": approach, 
        "approach_label": ( 
            "Best Score" 
            if normalized_approach in {"best_score", "explicit_model"} 
            else "Combined Score" 
        ), 
        "phase5_recommended_model": phase5_top_model, 
        "phase5_recommended_model_full_name": DISPLAY_NAMES.get(phase5_top_model, phase5_top_model), 
        "selected_model": selected_model, 
        "selected_model_full_name": selected_model_full_name, 
        "trained_model": actual_trained_model, 
        "trained_model_full_name": actual_trained_model_full_name, 
        "trained_models": trained_model_names, 
        "trained_model_full_names": [DISPLAY_NAMES.get(name, name) for name in trained_model_names], 
        "models": normalized_weighted, 
        "model_failures": failures, 
        "target_columns": target_columns, 
        "explain_by_columns": explain_by_columns, 
        "investigation_columns": visible_columns, 
        "records_analyzed": int(len(df)), 
        "total_records": int(len(df)), 
        "detected_anomalies": anomaly_count, 
        "normal_records": normal_count, 
        "anomaly_rate": anomaly_rate, 
        "contamination": detected_contamination, 
        "contamination_percentage": anomaly_rate, 
        "configured_contamination": float(contamination), 
        "configured_contamination_percentage": float(contamination * 100.0), 
        "pyod_contamination": pyod_contamination, 
        "pyod_contaminations": pyod_contaminations, 
        "contamination_source": "actual_backend_anomaly_labels", 
        "configured_contamination_source": "phase6_request", 
        "pyod_contamination_source": "fitted_pyod_model_contamination", 
        "threshold": float(threshold), 
        "threshold_method": threshold_method, 
        "threshold_explanation": detection_rule, 
        "visualization": visualization, 
        "filter_schema": _filter_schema(df, visible_columns), 
        "records": records, 
        "records_include_backend_status": True, 
        "records_include_all_analyzed_rows": True, 
        "normal_records_have_status": "Normal", 
        "anomaly_records_have_status": "Anomaly", 
        "range_evidence_configuration": {
            "columns": range_columns,
            "statistics": range_statistics,
            "formula": "(actual - minimum) / (maximum - minimum) * 100",
            "minimum_position_percent": 0.0,
            "maximum_position_percent": 100.0,
            "source": "same Phase 3 dataframe supplied to PyOD detection",
            "purpose": "Dynamic UI value-position bar; not a replacement for the PyOD anomaly score or threshold.",
        },
        "feature_engineering": { 
            "feature_count": int(feature_matrix.X.shape[1]), 
            "feature_names": feature_matrix.feature_names, 
            "feature_sources": feature_matrix.feature_sources, 
            "source_types": feature_matrix.source_types, 
            "detection_uses_only_target_columns": True, 
            "explain_by_used_as_detection_features": False, 
            "description": ( 
                "Features were generated dynamically from only the user-selected Target / Detection Columns. " 
                "Explain By Columns remain available for investigation and explanation and are not silently added to anomaly detection." 
            ), 
        }, 
        "explainability_configuration": { 
            "target_columns": target_columns, 
            "explain_by_columns": explain_by_columns, 
            "detection_feature_sources": feature_matrix.feature_sources, 
            "target_columns_are_model_features": True, 
            "explain_by_columns_are_context": True, 
            "note": ( 
                "Explain By columns are explicitly forwarded to the explainability module. They provide investigative " 
                "context and are not automatically treated as detection features. SHAP is used only where the actual " 
                "model inputs support it; unsupported causal claims are not fabricated." 
            ), 
        }, 
        "objective": phase4_objective or {}, 
        "training": { 
            "status": "completed" if not failures else "completed_with_failures", 
            "library": "PyOD", 
            "selected_models": requested_model_names, 
            "trained_models": [ 
                { 
                    "model": name, 
                    "display_name": DISPLAY_NAMES.get(name, name), 
                    "status": "completed", 
                } 
                for name in trained_model_names 
            ], 
            "stages": [ 
                {"key": "prepare", "label": "Preparing selected features", "status": "completed"}, 
                {"key": "model_inputs", "label": "Preparing PyOD model inputs", "status": "completed"}, 
                {"key": "models", "label": "Training selected PyOD model(s)", "status": "completed"}, 
                {"key": "scores", "label": "Calculating anomaly scores", "status": "completed"}, 
                {"key": "threshold", "label": "Applying PyOD threshold handling", "status": "completed"}, 
                {"key": "classification", "label": "Classifying records as Normal or Anomaly", "status": "completed"}, 
            ], 
        }, 
        "detection": { 
            "status": "completed", 
            "library": "PyOD", 
            "trained_models": trained_model_names, 
            "score_source": "PyOD decision_scores_ or decision_function()", 
            "threshold": float(threshold), 
            "threshold_method": threshold_method, 
            "total_records": int(len(df)), 
            "anomaly_records": anomaly_count, 
            "normal_records": normal_count, 
            "anomaly_rate": anomaly_rate, 
            "contamination": detected_contamination, 
            "pyod_contamination": pyod_contamination, 
            "pyod_contaminations": pyod_contaminations, 
            "contamination_source": "actual_backend_anomaly_labels", 
            "backend_source_of_truth": True, 
        }, 
        "status": "completed", 
    } 
