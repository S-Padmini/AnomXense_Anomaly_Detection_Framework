from __future__ import annotations

from typing import Any

import base64
import io
import re

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .evaluation import evaluate_detection


class UnivariateDetector:
    """
    Univariate statistical anomaly detection using the IQR method.

    IMPORTANT:
    This detector must receive the Phase 3 preprocessed dataframe.
    It does not access or process the raw dataset.

    IQR is applied only to numerical columns because categorical,
    identifier, and other non-numerical values are not suitable for
    direct IQR-based anomaly detection.
    """

    METHOD = "IQR"

    def __init__(self, dataframe: pd.DataFrame):
        if dataframe is None:
            raise ValueError("Preprocessed dataframe cannot be None.")

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("UnivariateDetector expects a pandas DataFrame.")

        if dataframe.empty:
            raise ValueError("Preprocessed dataframe is empty.")

        self.dataframe = dataframe.copy()

    def get_eligible_columns(self) -> list[str]:
        eligible: list[str] = []

        for column in self.dataframe.columns:
            series = self.dataframe[column]

            if pd.api.types.is_bool_dtype(series):
                continue

            if pd.api.types.is_numeric_dtype(series):
                eligible.append(str(column))

        return eligible

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None:
            return None

        if pd.isna(value):
            return None

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            return float(value)

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        return value

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "missing"

        if isinstance(value, (float, np.floating)):
            if np.isfinite(value):
                return f"{float(value):.6g}"

        return str(value)

    def _calculate_boundaries(
        self,
        series: pd.Series,
    ) -> dict[str, float]:
        numeric = pd.to_numeric(
            series,
            errors="coerce",
        ).dropna()

        if numeric.empty:
            raise ValueError(
                "Column contains no valid numerical values."
            )

        q1 = float(numeric.quantile(0.25))
        q3 = float(numeric.quantile(0.75))
        iqr = float(q3 - q1)

        iqr_lower_fence = float(
            q1 - (1.5 * iqr)
        )

        upper_boundary = float(
            q3 + (1.5 * iqr)
        )

        if float(numeric.min()) >= 0 and iqr_lower_fence < 0:
            lower_boundary = 0.0
        else:
            lower_boundary = iqr_lower_fence

        return {
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "iqr_lower_fence": iqr_lower_fence,
            "lower_boundary": lower_boundary,
            "upper_boundary": upper_boundary,
        }

    @staticmethod
    def _build_record_reason(
        value: float,
        lower_boundary: float,
        upper_boundary: float,
        is_anomaly: bool,
    ) -> str:
        value_text = UnivariateDetector._format_value(value)
        lower_text = UnivariateDetector._format_value(lower_boundary)
        upper_text = UnivariateDetector._format_value(upper_boundary)

        if value < lower_boundary:
            return (
                f"{value_text} is below the lower IQR boundary "
                f"of {lower_text}, so this record is classified as an anomaly."
            )

        if value > upper_boundary:
            return (
                f"{value_text} is above the upper IQR boundary "
                f"of {upper_text}, so this record is classified as an anomaly."
            )

        if is_anomaly:
            return (
                f"{value_text} falls outside the calculated IQR boundaries, "
                f"so this record is classified as an anomaly."
            )

        return (
            f"{value_text} lies within the IQR boundaries "
            f"of {lower_text} to {upper_text}, so this record is classified as normal."
        )

    @staticmethod
    def _build_boundary_comparison(
        value: float,
        lower_boundary: float,
        upper_boundary: float,
    ) -> str:
        value_text = UnivariateDetector._format_value(value)
        lower_text = UnivariateDetector._format_value(lower_boundary)
        upper_text = UnivariateDetector._format_value(upper_boundary)

        if value < lower_boundary:
            return f"{value_text} < lower boundary {lower_text}"

        if value > upper_boundary:
            return f"{value_text} > upper boundary {upper_text}"

        return f"{lower_text} ≤ {value_text} ≤ {upper_text}"

    def detect_column(
        self,
        column_name: str,
    ) -> dict[str, Any]:
        if column_name not in self.dataframe.columns:
            raise ValueError(
                f"Column '{column_name}' does not exist in the "
                "Phase 3 preprocessed dataframe."
            )

        series = self.dataframe[column_name]

        if pd.api.types.is_bool_dtype(series):
            raise ValueError(
                f"Column '{column_name}' is boolean and is not eligible "
                "for IQR-based univariate detection."
            )

        if not pd.api.types.is_numeric_dtype(series):
            raise ValueError(
                f"Column '{column_name}' is not numerical and is not "
                "eligible for IQR-based univariate detection."
            )

        boundaries = self._calculate_boundaries(series)

        lower_boundary = boundaries["lower_boundary"]
        upper_boundary = boundaries["upper_boundary"]

        numeric_values = pd.to_numeric(
            series,
            errors="coerce",
        )

        record_results: list[dict[str, Any]] = []

        anomaly_count = 0
        normal_count = 0

        for position, (index, raw_value) in enumerate(
            numeric_values.items(),
            start=1,
        ):
            value = self._json_safe(raw_value)

            if value is None:
                status = "Normal"
                is_anomaly = False
                normal_count += 1

                comparison = "Value is missing after preprocessing."

                reason = (
                    "The value is missing in the Phase 3 preprocessed data, "
                    "so it is not classified as an IQR anomaly."
                )

            else:
                numeric_value = float(value)

                is_anomaly = (
                    numeric_value < lower_boundary
                    or numeric_value > upper_boundary
                )

                status = "Anomaly" if is_anomaly else "Normal"

                if is_anomaly:
                    anomaly_count += 1
                else:
                    normal_count += 1

                comparison = self._build_boundary_comparison(
                    numeric_value,
                    lower_boundary,
                    upper_boundary,
                )

                reason = self._build_record_reason(
                    numeric_value,
                    lower_boundary,
                    upper_boundary,
                    is_anomaly,
                )

            record_results.append(
                {
                    "record_number": position,
                    "dataframe_index": self._json_safe(index),
                    "column_name": str(column_name),
                    "column_value": value,
                    "lower_boundary": lower_boundary,
                    "upper_boundary": upper_boundary,
                    "boundary_comparison": comparison,
                    "status": status,
                    "is_anomaly": is_anomaly,
                    "reason": reason,
                }
            )

        total_records = len(record_results)

        anomaly_percentage = (
            (anomaly_count / total_records) * 100
            if total_records > 0
            else 0.0
        )

        return {
            "variability": "Univariate",
            "column_name": str(column_name),
            "column_dtype": str(series.dtype),
            "total_records": total_records,
            "anomaly_records": anomaly_count,
            "normal_records": normal_count,
            "anomaly_percentage": round(
                anomaly_percentage,
                2,
            ),
            "method_used": self.METHOD,
            "q1": boundaries["q1"],
            "q3": boundaries["q3"],
            "iqr": boundaries["iqr"],
            "iqr_lower_fence": boundaries["iqr_lower_fence"],
            "lower_boundary": lower_boundary,
            "upper_boundary": upper_boundary,
            "records": record_results,
        }

    def detect_all_columns(
        self,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for column_name in self.get_eligible_columns():
            results.append(
                self.detect_column(column_name)
            )

        return results

    def build_summary(
        self,
    ) -> list[dict[str, Any]]:
        all_results = self.detect_all_columns()

        summary: list[dict[str, Any]] = []

        for serial_number, result in enumerate(
            all_results,
            start=1,
        ):
            summary.append(
                {
                    "s_no": serial_number,
                    "column_name": result["column_name"],
                    "total_anomaly_records": result["anomaly_records"],
                    "anomaly_percentage": result["anomaly_percentage"],
                }
            )

        return summary


# ======================================================================
# Controlled evaluation helpers
# ======================================================================

def _select_evaluation_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Select a deterministic numerical column for controlled evaluation.

    The first eligible numerical column with at least four valid values
    is selected.
    """

    for column in dataframe.columns:
        series = dataframe[column]

        if pd.api.types.is_bool_dtype(series):
            continue

        if not pd.api.types.is_numeric_dtype(series):
            continue

        numeric = pd.to_numeric(
            series,
            errors="coerce",
        ).dropna()

        if len(numeric) >= 4:
            return str(column)

    raise ValueError(
        "Accuracy evaluation requires at least one numerical column "
        "with four or more valid records."
    )


def _inject_statistical_perturbations(
    dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    list[int],
    dict[str, Any],
]:
    """
    Create a controlled evaluation dataset using statistically
    perturbed values.

    IMPORTANT:
    The perturbation is NOT generated by simply placing values beyond
    the IQR fence.

    Instead:
        1. A numerical column is selected.
        2. Robust statistics are calculated from the original values.
        3. A small deterministic sample of records is selected.
        4. Their values are perturbed using a robust scale derived
           from the original distribution.
        5. Ground-truth labels are retained separately.
        6. The normal IQR detector is run independently afterwards.

    The original dataframe is never modified.
    """

    evaluation_df = dataframe.copy(
        deep=True
    )

    column_name = _select_evaluation_column(
        evaluation_df
    )

    # Convert only the temporary evaluation column to float64.
    # This prevents errors when the original column is int64.
    evaluation_df[column_name] = (
        pd.to_numeric(
            evaluation_df[column_name],
            errors="coerce",
        ).astype("float64")
    )

    numeric = evaluation_df[column_name]

    valid_positions = np.flatnonzero(
        numeric.notna().to_numpy()
    )

    if len(valid_positions) < 4:
        raise ValueError(
            "Accuracy evaluation requires at least four valid numerical "
            "records in the selected column."
        )

    valid_values = (
        numeric.iloc[valid_positions]
        .astype(float)
    )

    # ------------------------------------------------------------------
    # Robust statistics from the ORIGINAL data
    # ------------------------------------------------------------------

    median_value = float(
        valid_values.median()
    )

    q1 = float(
        valid_values.quantile(0.25)
    )

    q3 = float(
        valid_values.quantile(0.75)
    )

    iqr = float(
        q3 - q1
    )

    mad = float(
        np.median(
            np.abs(
                valid_values.to_numpy()
                - median_value
            )
        )
    )

    standard_deviation = float(
        valid_values.std(
            ddof=0
        )
    )

    minimum_value = float(
        valid_values.min()
    )

    maximum_value = float(
        valid_values.max()
    )

    data_range = float(
        maximum_value - minimum_value
    )

    if not np.isfinite(data_range) or data_range <= 0:
        data_range = max(
            abs(maximum_value),
            abs(minimum_value),
            1.0,
        )

    # A robust scale is preferred. MAD is resistant to existing
    # outliers. IQR and standard deviation are fallback scales.
    robust_scale = max(
        mad * 1.4826,
        iqr / 1.349,
        standard_deviation,
        data_range * 0.01,
        1e-9,
    )

    # ------------------------------------------------------------------
    # Controlled sample size
    # ------------------------------------------------------------------

    injection_count = max(
        1,
        int(
            round(
                len(valid_positions) * 0.05
            )
        ),
    )

    injection_count = min(
        injection_count,
        len(valid_positions),
    )

    # Fixed seed makes the experiment reproducible.
    random_generator = np.random.default_rng(
        42
    )

    selected_row_positions = (
        random_generator.choice(
            valid_positions,
            size=injection_count,
            replace=False,
        )
        .astype(int)
        .tolist()
    )

    selected_row_positions.sort()

    # Ground truth:
    # 0 = normal
    # 1 = injected anomaly
    ground_truth_labels = [
        0
        for _ in range(len(evaluation_df))
    ]

    # ------------------------------------------------------------------
    # Statistical perturbation
    # ------------------------------------------------------------------
    #
    # The injected value is generated relative to the ORIGINAL value.
    # The perturbation magnitude is based on robust statistics rather
    # than the IQR anomaly boundary.
    #
    # A multiplier around 2.75 robust scales is used. This creates
    # meaningful distributional shifts without explicitly calculating
    # "upper fence + margin" or "lower fence - margin".
    #
    # This is deliberately independent from the detector's IQR rule.
    # ------------------------------------------------------------------

    perturbation_multiplier = 2.75

    perturbation_scale = (
        perturbation_multiplier
        * robust_scale
    )

    perturbation_details: list[dict[str, Any]] = []

    for anomaly_number, row_position in enumerate(
        selected_row_positions
    ):

        original_value = float(
            evaluation_df.iloc[
                row_position,
                evaluation_df.columns.get_loc(
                    column_name
                ),
            ]
        )

        # Alternate the direction to avoid making every artificial
        # anomaly move in exactly the same direction.
        if anomaly_number % 2 == 0:
            direction = 1.0
        else:
            direction = -1.0

        injected_value = (
            original_value
            + (
                direction
                * perturbation_scale
            )
        )

        # Keep the value finite.
        if not np.isfinite(injected_value):
            injected_value = (
                original_value
                + direction
                * data_range
            )

        evaluation_df.iloc[
            row_position,
            evaluation_df.columns.get_loc(
                column_name
            ),
        ] = float(
            injected_value
        )

        ground_truth_labels[
            row_position
        ] = 1

        perturbation_details.append(
            {
                "row_position": int(row_position),
                "original_value": float(
                    original_value
                ),
                "injected_value": float(
                    injected_value
                ),
                "direction": (
                    "upper"
                    if direction > 0
                    else "lower"
                ),
                "perturbation_magnitude": float(
                    abs(
                        injected_value
                        - original_value
                    )
                ),
            }
        )

    metadata = {
        "evaluation_column": column_name,
        "injected_anomaly_count": int(
            injection_count
        ),
        "injected_anomaly_percentage": round(
            (
                injection_count
                / len(evaluation_df)
            )
            * 100,
            2,
        ),
        "random_seed": 42,
        "median": median_value,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "mad": mad,
        "standard_deviation": standard_deviation,
        "robust_scale": float(
            robust_scale
        ),
        "perturbation_multiplier": (
            perturbation_multiplier
        ),
        "perturbation_scale": float(
            perturbation_scale
        ),
        "injection_rule": (
            "Known anomalies were created by statistically perturbing "
            "selected numerical values using a robust scale derived "
            "from the original data. The IQR detector was then run "
            "independently on the modified evaluation copy."
        ),
        "perturbations": perturbation_details,
    }

    return (
        evaluation_df,
        ground_truth_labels,
        metadata,
    )


def _evaluate_univariate_accuracy(
    preprocessed_df: pd.DataFrame,
) -> tuple[
    float,
    dict[str, Any],
]:
    """
    Evaluate IQR detection using controlled statistical perturbation.

    Ground-truth labels are created before detection and are never
    supplied to the detector itself.
    """

    (
        evaluation_df,
        actual_labels,
        evaluation_metadata,
    ) = _inject_statistical_perturbations(
        preprocessed_df
    )

    evaluation_detector = UnivariateDetector(
        evaluation_df
    )

    evaluation_column = evaluation_metadata[
        "evaluation_column"
    ]

    # Run the ordinary IQR detector independently.
    evaluation_result = (
        evaluation_detector.detect_column(
            evaluation_column
        )
    )

    predicted_labels = [
        1 if record.get("is_anomaly") else 0
        for record in evaluation_result.get(
            "records",
            [],
        )
    ]

    evaluation = evaluate_detection(
        actual_labels=actual_labels,
        predicted_labels=predicted_labels,
    )

    evaluation.update(
        {
            "evaluation_column": evaluation_column,
            "injected_anomaly_count": evaluation_metadata[
                "injected_anomaly_count"
            ],
            "injected_anomaly_percentage": evaluation_metadata[
                "injected_anomaly_percentage"
            ],
            "random_seed": evaluation_metadata[
                "random_seed"
            ],
            "evaluation_rule": evaluation_metadata[
                "injection_rule"
            ],
            "evaluation_median": evaluation_metadata[
                "median"
            ],
            "evaluation_q1": evaluation_metadata[
                "q1"
            ],
            "evaluation_q3": evaluation_metadata[
                "q3"
            ],
            "evaluation_iqr": evaluation_metadata[
                "iqr"
            ],
            "evaluation_mad": evaluation_metadata[
                "mad"
            ],
            "evaluation_robust_scale": evaluation_metadata[
                "robust_scale"
            ],
            "evaluation_perturbation_multiplier": (
                evaluation_metadata[
                    "perturbation_multiplier"
                ]
            ),
        }
    )

    return (
        float(
            evaluation["accuracy"]
        ),
        evaluation,
    )


# ======================================================================
# PDF helpers
# ======================================================================

def _safe_report_name(
    dataset_name: str,
) -> str:
    """Create a safe downloadable PDF filename."""

    stem = str(
        dataset_name or "ANOMALY_Dataset"
    )

    stem = re.sub(
        r"\.[^.]+$",
        "",
        stem,
    )

    stem = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        stem,
    ).strip(
        "._-"
    )

    return (
        f"{stem or 'ANOMALY_Dataset'}"
        "_Univariate_Anomaly_Report.pdf"
    )


def _report_value(
    value: Any,
) -> str:
    if value is None:
        return "—"

    if isinstance(value, float):
        return f"{value:.6g}"

    return str(value)


def _build_univariate_pdf(
    dataset_name: str,
    preprocessed_df: pd.DataFrame,
    results: list[dict[str, Any]],
    summary: list[dict[str, Any]],
) -> bytes:
    """Build the Univariate report as a clean A4 PDF with no visualizations."""

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Univariate Anomaly Detection Report",
        author="ANOMALY",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#173f8a"),
        alignment=TA_LEFT,
        spaceAfter=5 * mm,
    )

    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#4f5f78"),
        spaceAfter=2 * mm,
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#102f68"),
        spaceBefore=4 * mm,
        spaceAfter=2.5 * mm,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=7.2,
        leading=9.2,
        textColor=colors.HexColor("#172033"),
    )

    small_center = ParagraphStyle(
        "SmallCenter",
        parent=small_style,
        alignment=TA_CENTER,
    )

    header_style = ParagraphStyle(
        "Header",
        parent=small_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    story = [
        Paragraph(
            "Univariate Anomaly Detection Report",
            title_style,
        ),
        Paragraph(
            f"<b>Dataset:</b> {_report_value(dataset_name)}",
            meta_style,
        ),
        Paragraph(
            f"<b>No. of records:</b> {len(preprocessed_df)}",
            meta_style,
        ),
        Paragraph(
            f"<b>No. of attributes:</b> {len(preprocessed_df.columns)}",
            meta_style,
        ),
        Paragraph(
            "<b>Method used:</b> IQR (Interquartile Range)",
            meta_style,
        ),
        Paragraph(
            "<b>Variability:</b> Univariate",
            meta_style,
        ),
        Spacer(
            1,
            3 * mm,
        ),
        Paragraph(
            "Anomaly Summary",
            section_style,
        ),
    ]

    summary_data = [[
        Paragraph(
            "Column Name",
            header_style,
        ),
        Paragraph(
            "Anomaly No.",
            header_style,
        ),
        Paragraph(
            "Anomaly %",
            header_style,
        ),
    ]]

    for item in summary:
        summary_data.append([
            Paragraph(
                _report_value(
                    item.get("column_name")
                ),
                small_style,
            ),
            Paragraph(
                _report_value(
                    item.get(
                        "total_anomaly_records"
                    )
                ),
                small_center,
            ),
            Paragraph(
                f"{_report_value(item.get('anomaly_percentage'))}%",
                small_center,
            ),
        ])

    summary_table = Table(
        summary_data,
        colWidths=[
            95 * mm,
            35 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    summary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#173f8a"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#c9d3e5"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
        ])
    )

    story += [
        summary_table,
        Spacer(
            1,
            5 * mm,
        ),
    ]

    for column_result in results:
        column_name = column_result.get(
            "column_name",
            "Column",
        )

        story.append(
            Paragraph(
                f"Column: {_report_value(column_name)}",
                section_style,
            )
        )

        stats_data = [
            [
                Paragraph(
                    "Q1",
                    header_style,
                ),
                Paragraph(
                    "Q3",
                    header_style,
                ),
                Paragraph(
                    "IQR",
                    header_style,
                ),
                Paragraph(
                    "Lower",
                    header_style,
                ),
                Paragraph(
                    "Upper",
                    header_style,
                ),
                Paragraph(
                    "Anomaly No.",
                    header_style,
                ),
            ],
            [
                Paragraph(
                    _report_value(
                        column_result.get("q1")
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        column_result.get("q3")
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        column_result.get("iqr")
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        column_result.get(
                            "lower_boundary"
                        )
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        column_result.get(
                            "upper_boundary"
                        )
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        column_result.get(
                            "anomaly_records"
                        )
                    ),
                    small_center,
                ),
            ],
        ]

        stats_table = Table(
            stats_data,
            colWidths=[
                27 * mm,
                27 * mm,
                27 * mm,
                27 * mm,
                27 * mm,
                27 * mm,
            ],
            repeatRows=1,
        )

        stats_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#315f9d"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#c9d3e5"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ])
        )

        story += [
            stats_table,
            Spacer(
                1,
                3 * mm,
            ),
        ]

        record_heading = ParagraphStyle(
            "RecordHeading",
            parent=small_style,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#173f8a"),
            spaceAfter=1.5 * mm,
        )

        story.append(
            Paragraph(
                "Record Values and Anomaly Comparison",
                record_heading,
            )
        )

        record_data = [[
            Paragraph(
                "Record",
                header_style,
            ),
            Paragraph(
                "Value",
                header_style,
            ),
            Paragraph(
                "Compare",
                header_style,
            ),
            Paragraph(
                "Why Anomaly",
                header_style,
            ),
            Paragraph(
                "Status",
                header_style,
            ),
        ]]

        for record in column_result.get(
            "records",
            [],
        ):
            if not record.get("is_anomaly"):
                continue

            record_data.append([
                Paragraph(
                    _report_value(
                        record.get(
                            "record_number"
                        )
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        record.get(
                            "column_value"
                        )
                    ),
                    small_center,
                ),
                Paragraph(
                    _report_value(
                        record.get(
                            "boundary_comparison"
                        )
                    ),
                    small_style,
                ),
                Paragraph(
                    _report_value(
                        record.get(
                            "reason"
                        )
                    ),
                    small_style,
                ),
                Paragraph(
                    _report_value(
                        record.get(
                            "status"
                        )
                    ),
                    small_center,
                ),
            ])

        record_table = Table(
            record_data,
            colWidths=[
                15 * mm,
                23 * mm,
                47 * mm,
                77 * mm,
                18 * mm,
            ],
            repeatRows=1,
        )

        record_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#173f8a"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#d2dae8"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3.5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3.5,
                ),
            ])
        )

        story += [
            record_table,
            Spacer(
                1,
                5 * mm,
            ),
        ]

    def add_page_number(
        canvas,
        doc,
    ):
        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            8,
        )

        canvas.setFillColor(
            colors.HexColor("#68758a")
        )

        canvas.drawRightString(
            A4[0] - 14 * mm,
            8 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return buffer.getvalue()


# ======================================================================
# Main detection function
# ======================================================================

def detect_univariate(
    preprocessed_df: pd.DataFrame,
    dataset_name: str = "ANOMALY Dataset",
    actual_labels: list[int] | None = None,
) -> dict[str, Any]:
    """
    Run IQR detection and generate the downloadable A4 PDF report.

    Normal detection uses the actual Phase 3 preprocessed dataframe.

    Accuracy is automatically evaluated using a separate controlled
    evaluation copy containing statistically perturbed values with
    known ground-truth labels.

    The original Phase 3 dataframe is never modified.

    The optional actual_labels parameter is retained for compatibility
    with existing callers.
    """

    detector = UnivariateDetector(
        preprocessed_df
    )

    results = detector.detect_all_columns()

    summary = detector.build_summary()

    accuracy: float | None = None

    evaluation: dict[str, Any] | None = None

    if actual_labels is not None:

        if len(results) != 1:
            raise ValueError(
                "Explicit accuracy evaluation for Univariate detection "
                "requires ground-truth labels for a single evaluated column."
            )

        predicted_labels = [
            1 if record.get("is_anomaly") else 0
            for record in results[0].get(
                "records",
                [],
            )
        ]

        evaluation = evaluate_detection(
            actual_labels=actual_labels,
            predicted_labels=predicted_labels,
        )

        accuracy = float(
            evaluation["accuracy"]
        )

    else:

        (
            accuracy,
            evaluation,
        ) = _evaluate_univariate_accuracy(
            preprocessed_df
        )

    pdf_bytes = _build_univariate_pdf(
        dataset_name=dataset_name,
        preprocessed_df=preprocessed_df,
        results=results,
        summary=summary,
    )

    return {
        "variability": "Univariate",
        "method_used": UnivariateDetector.METHOD,
        "eligible_columns": detector.get_eligible_columns(),
        "number_of_attributes": int(
            len(preprocessed_df.columns)
        ),
        "total_records": int(
            len(preprocessed_df)
        ),
        "dataset_name": str(
            dataset_name
        ),
        "summary": summary,
        "results": results,
        "accuracy": accuracy,
        "evaluation": evaluation,
        "pdf_base64": base64.b64encode(
            pdf_bytes
        ).decode("ascii"),
        "pdf_filename": _safe_report_name(
            dataset_name
        ),
    }