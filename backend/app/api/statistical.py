from __future__ import annotations

from typing import Any

import base64

from fastapi import APIRouter, HTTPException

from app.core.store import store

from app.phases.statistical.explainability import (
    MahalanobisExplainability,
)

from app.phases.statistical.multivariate import (
    MultivariateDetector,
    detect_multivariate,
    _build_multivariate_pdf,
    _safe_report_name,
)

from app.phases.statistical.univariate import (
    UnivariateDetector,
    detect_univariate,
)

from app.schemas.statistical_schema import (
    MultivariateExplainRequest,
    MultivariateExplainResponse,
    MultivariateResponse,
    StatisticalApproachRequest,
    StatisticalApproachResponse,
    UnivariateResponse,
)


router = APIRouter(
    prefix="/api/statistical",
    tags=["Statistical Approach"],
)


# ======================================================================
# Store helpers
# ======================================================================


def _get_session(
    dataset_id: str,
) -> Any:
    """
    Retrieve the existing dataset session.
    """

    if not dataset_id:
        raise HTTPException(
            status_code=400,
            detail="dataset_id is required.",
        )

    try:
        session = store.get(
            dataset_id
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset session '{dataset_id}' "
                "was not found."
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset session '{dataset_id}' "
                "could not be retrieved."
            ),
        ) from exc

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset session '{dataset_id}' "
                "was not found."
            ),
        )

    return session


def _get_preprocessed_dataframe(
    dataset_id: str,
):
    """
    Retrieve ONLY the Phase 3 preprocessed dataframe.

    Statistical detection must never fall back to the raw dataframe.
    """

    session = _get_session(
        dataset_id
    )

    preprocessed_df = getattr(
        session,
        "preprocessed_df",
        None,
    )

    if preprocessed_df is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Phase 3 preprocessing has not been completed "
                f"for dataset '{dataset_id}'."
            ),
        )

    if preprocessed_df.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "The Phase 3 preprocessed dataset is empty."
            ),
        )

    return preprocessed_df


def _get_dataset_name(
    dataset_id: str,
) -> str:
    """
    Retrieve the original dataset name when available.
    """

    session = _get_session(
        dataset_id
    )

    for attribute in (
        "dataset_name",
        "filename",
        "file_name",
        "original_filename",
        "name",
    ):
        value = getattr(
            session,
            attribute,
            None,
        )

        if value:
            return str(value)

    return (
        f"ANOMALY_Dataset_{dataset_id}"
    )


# ======================================================================
# Approach selection
# ======================================================================


@router.post(
    "/approach",
    response_model=StatisticalApproachResponse,
)
def select_statistical_approach(
    request: StatisticalApproachRequest,
):
    """
    Store/confirm the statistical approach selected by the user.
    """

    approach = (
        request.approach
        .strip()
        .lower()
    )

    if approach not in {
        "univariate",
        "multivariate",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid statistical approach. "
                "Use 'univariate' or 'multivariate'."
            ),
        )

    session = _get_session(
        request.dataset_id
    )

    session.statistical_approach = (
        approach
    )

    return StatisticalApproachResponse(
        dataset_id=request.dataset_id,
        approach=approach,
        message=(
            f"{approach.capitalize()} "
            "statistical approach selected."
        ),
    )


# ======================================================================
# Univariate
# ======================================================================


@router.get(
    "/{dataset_id}/univariate",
    response_model=UnivariateResponse,
)
def run_univariate(
    dataset_id: str,
):
    """
    Run IQR-based univariate anomaly detection.

    Only the Phase 3 preprocessed dataframe is supplied to the detector.

    Accuracy is automatically evaluated inside detect_univariate()
    using a separate controlled evaluation dataset with known
    statistically injected anomalies.
    """

    preprocessed_df = (
        _get_preprocessed_dataframe(
            dataset_id
        )
    )

    try:
        dataset_name = (
            _get_dataset_name(
                dataset_id
            )
        )

        result = detect_univariate(
            preprocessed_df,
            dataset_name=dataset_name,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Univariate statistical analysis failed: "
                f"{exc}"
            ),
        ) from exc


# ======================================================================
# Univariate column details
# ======================================================================


@router.get(
    "/{dataset_id}/univariate/{column_name}",
)
def run_univariate_column(
    dataset_id: str,
    column_name: str,
):
    """
    Return detailed IQR analysis for one numerical column.
    """

    preprocessed_df = (
        _get_preprocessed_dataframe(
            dataset_id
        )
    )

    try:
        detector = UnivariateDetector(
            preprocessed_df
        )

        return detector.detect_column(
            column_name
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Univariate column analysis failed."
            ),
        ) from exc


# ======================================================================
# Multivariate
# ======================================================================


@router.get(
    "/{dataset_id}/multivariate",
    response_model=MultivariateResponse,
)
def run_multivariate(
    dataset_id: str,
):
    """
    Run Mahalanobis Distance anomaly detection.

    IMPORTANT:
    - Uses Phase 3 preprocessed data only.
    - Uses all usable features supplied to the detector.
    - Does not ask the user for another feature selection.
    - The score displayed by the frontend is the detector's
      actual Mahalanobis distance.
    - Accuracy is automatically evaluated inside
      detect_multivariate() using a separate controlled
      evaluation dataset.
    """

    preprocessed_df = (
        _get_preprocessed_dataframe(
            dataset_id
        )
    )

    try:
        # --------------------------------------------------------------
        # 1. Run the normal Mahalanobis detector.
        #
        # detect_multivariate() also performs the controlled
        # accuracy evaluation on a separate copy of the data.
        # --------------------------------------------------------------

        result = detect_multivariate(
            preprocessed_df
        )

        # --------------------------------------------------------------
        # 2. Add the actual dataset name.
        # --------------------------------------------------------------

        dataset_name = (
            _get_dataset_name(
                dataset_id
            )
        )

        result[
            "dataset_name"
        ] = dataset_name

        # --------------------------------------------------------------
        # 3. Rebuild the PDF using the actual dataset name.
        #
        # This does NOT affect detection or accuracy.
        # --------------------------------------------------------------

        pdf_bytes = (
            _build_multivariate_pdf(
                dataset_name,
                preprocessed_df,
                result,
            )
        )

        result[
            "pdf_base64"
        ] = base64.b64encode(
            pdf_bytes
        ).decode(
            "ascii"
        )

        result[
            "pdf_filename"
        ] = _safe_report_name(
            dataset_name
        )

        # --------------------------------------------------------------
        # 4. Normalize the score fields for the UI.
        #
        # The canonical detector score is:
        #
        #     mah_distance
        #
        # The frontend also understands:
        #
        #     mahalanobis_score
        #
        # Both refer to exactly the same backend value.
        # --------------------------------------------------------------

        records = result.get(
            "records",
            [],
        )

        threshold = result.get(
            "threshold"
        )

        normalized_records = []

        for record in records:

            normalized = dict(
                record
            )

            actual_score = (
                normalized.get(
                    "mah_distance"
                )
            )

            if actual_score is None:
                actual_score = (
                    normalized.get(
                        "mahalanobis_score"
                    )
                )

            if actual_score is not None:

                actual_score = float(
                    actual_score
                )

                normalized[
                    "mah_distance"
                ] = actual_score

                normalized[
                    "mahalanobis_score"
                ] = actual_score

                if threshold is not None:

                    normalized[
                        "threshold"
                    ] = float(
                        threshold
                    )

                    normalized[
                        "is_anomaly"
                    ] = (
                        actual_score
                        > float(
                            threshold
                        )
                    )

                    normalized[
                        "status"
                    ] = (
                        "Anomaly"
                        if actual_score
                        > float(
                            threshold
                        )
                        else "Normal"
                    )

            normalized_records.append(
                normalized
            )

        result[
            "records"
        ] = normalized_records

        # --------------------------------------------------------------
        # 5. IMPORTANT:
        #
        # Accuracy and evaluation returned by detect_multivariate()
        # are intentionally preserved.
        #
        # They contain:
        #
        #     accuracy
        #     total_records
        #     TP
        #     TN
        #     FP
        #     FN
        #     injected anomaly information
        #     perturbation information
        #
        # No recalculation is performed here.
        # --------------------------------------------------------------

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Multivariate statistical analysis failed: "
                f"{exc}"
            ),
        ) from exc


# ======================================================================
# Multivariate record explanation
# ======================================================================


@router.post(
    "/{dataset_id}/multivariate/explain",
    response_model=MultivariateExplainResponse,
)
def explain_multivariate_record(
    dataset_id: str,
    request: MultivariateExplainRequest,
):
    """
    Dynamically explain one Mahalanobis record.

    Detection and explanation use the same current
    Phase 3 preprocessed dataframe.

    The Mahalanobis score comes directly from the
    MultivariateDetector result.

    The explanation itself is generated by
    MahalanobisExplainability.

    SHAP is optional inside the explainability layer.
    If SHAP is unavailable or fails internally, the
    explainability layer should fall back to the exact
    Mahalanobis contribution calculation.
    """

    preprocessed_df = (
        _get_preprocessed_dataframe(
            dataset_id
        )
    )

    try:
        # --------------------------------------------------------------
        # 1. Run the existing Mahalanobis detector.
        # --------------------------------------------------------------

        detector = MultivariateDetector(
            preprocessed_df
        )

        detection_result = (
            detector.detect()
        )

        # --------------------------------------------------------------
        # 2. Validate requested record number.
        # --------------------------------------------------------------

        record_number = (
            request.record_number
        )

        if record_number < 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Record number must be greater than "
                    "or equal to 1."
                ),
            )

        available_records = (
            detection_result.get(
                "records",
                [],
            )
        )

        if record_number > len(
            available_records
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Record number {record_number} is outside "
                    "the available dataset records."
                ),
            )

        # --------------------------------------------------------------
        # 3. Retrieve the exact record selected by the user.
        # --------------------------------------------------------------

        detected_record = (
            available_records[
                record_number - 1
            ]
        )

        # --------------------------------------------------------------
        # 4. Retrieve the exact columns used by the detector.
        # --------------------------------------------------------------

        used_columns = (
            detection_result.get(
                "columns_involved",
                [],
            )
        )

        if not used_columns:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No usable numerical columns were available "
                    "for multivariate explanation."
                ),
            )

        # --------------------------------------------------------------
        # 5. Preserve the detector's actual Mahalanobis score.
        #
        # We do NOT replace the detector's score with a newly
        # calculated score here.
        # --------------------------------------------------------------

        actual_score = (
            detected_record.get(
                "mah_distance"
            )
        )

        if actual_score is None:
            actual_score = (
                detected_record.get(
                    "mahalanobis_score"
                )
            )

        if actual_score is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "The Mahalanobis detector did not return "
                    "a score for the selected record."
                ),
            )

        actual_score = float(
            actual_score
        )

        # --------------------------------------------------------------
        # 6. Retrieve the detector threshold.
        # --------------------------------------------------------------

        actual_threshold = (
            detection_result.get(
                "threshold"
            )
        )

        if actual_threshold is not None:
            actual_threshold = float(
                actual_threshold
            )

        # --------------------------------------------------------------
        # 7. Build the explanation service.
        # --------------------------------------------------------------

        explainer = (
            MahalanobisExplainability(
                dataframe=preprocessed_df,
                used_columns=used_columns,
            )
        )

        # --------------------------------------------------------------
        # 8. Generate feature-level explanation.
        #
        # The explanation layer handles:
        #
        # - exact Mahalanobis contribution
        # - top contributing features
        # - all feature contributions
        # - calculation information
        # - optional SHAP attribution
        #
        # SHAP must not replace the actual detector score.
        # --------------------------------------------------------------

        explanation = (
            explainer.explain_record(
                record_number=record_number,
                mah_distance=actual_score,
                threshold=actual_threshold,
                top_n=request.top_n,
            )
        )

        # --------------------------------------------------------------
        # 9. Validate explanation result.
        # --------------------------------------------------------------

        if explanation is None:
            raise ValueError(
                "The explainability service returned no result."
            )

        if not isinstance(
            explanation,
            dict,
        ):
            raise TypeError(
                "The explainability service returned "
                "an invalid response type."
            )

        # --------------------------------------------------------------
        # 10. Explicitly preserve the exact detector score.
        # --------------------------------------------------------------

        explanation[
            "mah_distance"
        ] = actual_score

        explanation[
            "mahalanobis_score"
        ] = actual_score

        if actual_threshold is not None:
            explanation[
                "threshold"
            ] = actual_threshold

        # --------------------------------------------------------------
        # 11. Preserve record identity.
        # --------------------------------------------------------------

        explanation[
            "record_number"
        ] = record_number

        # --------------------------------------------------------------
        # 12. Preserve detector columns.
        # --------------------------------------------------------------

        explanation[
            "columns_involved"
        ] = list(
            used_columns
        )

        return explanation

    except HTTPException:
        # Keep intentional API errors unchanged.
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Multivariate record explanation "
                f"validation failed: {str(exc)}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Multivariate record explanation failed: "
                f"{type(exc).__name__}: {str(exc)}"
            ),
        ) from exc