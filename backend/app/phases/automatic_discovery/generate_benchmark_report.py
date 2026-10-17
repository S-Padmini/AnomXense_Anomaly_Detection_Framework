from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"

    try:
        number = float(value)

        if not np.isfinite(number):
            return "—"

        return f"{number:.{digits}f}"

    except (TypeError, ValueError):
        return str(value)


def _safe_text(value: Any) -> str:
    try:
        from app.api.automatic_discovery import _json_safe

        value = _json_safe(value)

    except Exception:
        if value is None:
            return "—"

    if value is None:
        return "—"

    return str(value)


def _dataset_name(session: Any, dataset_id: str) -> str:
    candidates = (
        "filename",
        "file_name",
        "dataset_name",
        "original_filename",
        "original_file_name",
        "name",
    )

    for attribute in candidates:
        value = getattr(session, attribute, None)

        if value:
            return Path(str(value)).name

    return f"Dataset {dataset_id}"


def _paragraph(
    value: Any,
    styles,
    centered: bool = False,
):
    text = _safe_text(value)

    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    style = (
        styles["CellCenterCustom"]
        if centered
        else styles["CellCustom"]
    )

    return Paragraph(text, style)


# ============================================================================
# PDF STYLES
# ============================================================================

def _styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitleCustom",
            parent=styles["Title"],
            fontSize=16,
            leading=19,
            alignment=TA_CENTER,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitleCustom",
            parent=styles["BodyText"],
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionCustom",
            parent=styles["Heading2"],
            fontSize=10,
            leading=12,
            spaceBefore=5,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["BodyText"],
            fontSize=6.8,
            leading=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CellCustom",
            parent=styles["BodyText"],
            fontSize=5.8,
            leading=6.8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CellCenterCustom",
            parent=styles["BodyText"],
            fontSize=5.8,
            leading=6.8,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="HeaderCellCustom",
            parent=styles["BodyText"],
            fontSize=5.8,
            leading=6.5,
            alignment=TA_CENTER,
            textColor=colors.white,
        )
    )

    return styles


# ============================================================================
# COMMON TABLE STYLE
# ============================================================================

def _table_style():
    return TableStyle(
        [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#17324D"),
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold",
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "LEADING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.3,
                colors.HexColor("#94A3B8"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F5F7FA"),
                ],
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2.5,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                2.5,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2.5,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2.5,
            ),
        ]
    )


# ============================================================================
# REPORT HEADER
# ============================================================================

def _header_table(
    dataset_name: str,
    dataframe,
    columns: list[str],
    detection: dict[str, Any],
    styles,
):
    approach = (
        "Univariate"
        if detection.get("approach") == "univariate"
        else "Multivariate"
    )

    score_method = detection.get(
        "score_method",
        "combined_score",
    )

    method = (
        "Best Score"
        if score_method == "best_score"
        else "Combined Score"
    )

    if method == "Best Score":
        model_used = (
            detection.get("selected_model")
            or detection.get("model_name")
            or "—"
        )
    else:
        top_three = detection.get("models", [])[:3]

        model_used = ", ".join(
            str(item.get("model"))
            for item in top_three
            if item.get("model")
        )

        if not model_used:
            model_used = "—"

    rows = [
        [
            Paragraph(
                "<b>Machine Learning Anomaly Detection Report</b>",
                styles["SmallCustom"],
            ),
            "",
        ],
        [
            Paragraph(
                "<b>Dataset Filename</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                _safe_text(dataset_name),
                styles["SmallCustom"],
            ),
        ],
        [
            Paragraph(
                "<b>No. of Records</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                str(len(dataframe)),
                styles["SmallCustom"],
            ),
        ],
        [
            Paragraph(
                "<b>No. of Attributes</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                str(len(columns)),
                styles["SmallCustom"],
            ),
        ],
        [
            Paragraph(
                "<b>Approach Used</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                "Machine Learning Benchmarking Approach",
                styles["SmallCustom"],
            ),
        ],
        [
            Paragraph(
                "<b>Detection Method</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                method,
                styles["SmallCustom"],
            ),
        ],
        [
            Paragraph(
                "<b>Model Used</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                _safe_text(model_used),
                styles["SmallCustom"],
            ),
        ],
        [
            Paragraph(
                "<b>Variability</b>",
                styles["SmallCustom"],
            ),
            Paragraph(
                approach,
                styles["SmallCustom"],
            ),
        ],
    ]

    table = Table(
        rows,
        colWidths=[
            42 * mm,
            226 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "SPAN",
                    (0, 0),
                    (1, 0),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (1, 0),
                    colors.HexColor("#17324D"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#94A3B8"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (0, -1),
                    colors.HexColor("#EAF0F5"),
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
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    return table


# ============================================================================
# BENCHMARK SECTION
# ============================================================================

def _benchmark_section(
    story,
    detection: dict[str, Any],
    styles,
):
    story.append(
        Paragraph(
            "Machine Learning Benchmarking Results",
            styles["SectionCustom"],
        )
    )

    models = detection.get("models", [])

    rows = [
        [
            "Rank",
            "Model",
            "Benchmark Combined Score",
            "Ensemble Weight",
        ]
    ]

    for index, model in enumerate(models[:3], start=1):
        try:
            weight = float(
                model.get(
                    "weight",
                    0.0,
                )
            )
        except (TypeError, ValueError):
            weight = 0.0

        rows.append(
            [
                _paragraph(
                    index,
                    styles,
                    centered=True,
                ),
                _paragraph(
                    model.get("model"),
                    styles,
                ),
                _paragraph(
                    _fmt(
                        model.get(
                            "benchmark_combined_score"
                        )
                    ),
                    styles,
                    centered=True,
                ),
                _paragraph(
                    f"{weight * 100:.2f}%",
                    styles,
                    centered=True,
                ),
            ]
        )

    if len(rows) == 1:
        rows.append(
            [
                _paragraph(
                    "—",
                    styles,
                    centered=True,
                ),
                _paragraph(
                    "Benchmark information not available.",
                    styles,
                ),
                _paragraph(
                    "—",
                    styles,
                    centered=True,
                ),
                _paragraph(
                    "—",
                    styles,
                    centered=True,
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            18 * mm,
            78 * mm,
            78 * mm,
            50 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(_table_style())

    story.append(table)
    story.append(Spacer(1, 5))


# ============================================================================
# UNIVARIATE REPORT
# ============================================================================

def _univariate_report(
    story,
    detection: dict[str, Any],
    dataframe,
    columns: list[str],
    styles,
):
    from app.api.automatic_discovery import (
        _build_column_summaries,
        _column_ensemble_view,
    )

    # ------------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------------

    story.append(
        Paragraph(
            "Univariate Detection Summary",
            styles["SectionCustom"],
        )
    )

    summary_rows = [
        [
            "Column Name",
            "No. of Anomalies",
            "% of Anomalies",
        ]
    ]

    summaries = _build_column_summaries(
        detection
    )

    for item in summaries:
        summary_rows.append(
            [
                _paragraph(
                    item.get("column"),
                    styles,
                ),
                _paragraph(
                    item.get("anomaly_records"),
                    styles,
                    centered=True,
                ),
                _paragraph(
                    (
                        f"{float(item.get('anomaly_rate_percent', 0.0)):.4f}%"
                    ),
                    styles,
                    centered=True,
                ),
            ]
        )

    if len(summary_rows) == 1:
        summary_rows.append(
            [
                _paragraph(
                    "—",
                    styles,
                ),
                _paragraph(
                    "0",
                    styles,
                    centered=True,
                ),
                _paragraph(
                    "0.0000%",
                    styles,
                    centered=True,
                ),
            ]
        )

    summary_table = Table(
        summary_rows,
        colWidths=[
            125 * mm,
            55 * mm,
            55 * mm,
        ],
        repeatRows=1,
    )

    summary_table.setStyle(_table_style())

    story.append(summary_table)
    story.append(Spacer(1, 5))

    _benchmark_section(
        story,
        detection,
        styles,
    )

    story.append(
        Paragraph(
            "Detailed Univariate Results",
            styles["SectionCustom"],
        )
    )

    # ------------------------------------------------------------------------
    # EACH COLUMN
    # ------------------------------------------------------------------------

    for column_index, column in enumerate(columns):

        story.append(
            Paragraph(
                f"Column: {_safe_text(column)}",
                styles["SectionCustom"],
            )
        )

        scores, labels, threshold, model_views = (
            _column_ensemble_view(
                detection,
                column,
            )
        )

        rows = [
            [
                "Record",
                f"Value of {column}",
                "Anomaly Score",
                "Threshold",
            ]
        ]

        # ONLY ANOMALY RECORDS
        for index in range(len(scores)):

            if int(labels[index]) != 1:
                continue

            rows.append(
                [
                    _paragraph(
                        index + 1,
                        styles,
                        centered=True,
                    ),
                    _paragraph(
                        dataframe.iloc[index][column],
                        styles,
                    ),
                    _paragraph(
                        _fmt(
                            scores[index],
                            8,
                        ),
                        styles,
                    ),
                    _paragraph(
                        _fmt(
                            threshold,
                            8,
                        ),
                        styles,
                    ),
                ]
            )

        if len(rows) == 1:
            rows.append(
                [
                    _paragraph(
                        "—",
                        styles,
                        centered=True,
                    ),
                    _paragraph(
                        "No anomaly records detected.",
                        styles,
                    ),
                    _paragraph(
                        "—",
                        styles,
                        centered=True,
                    ),
                    _paragraph(
                        _fmt(
                            threshold,
                            8,
                        ),
                        styles,
                    ),
                ]
            )

        detail_table = Table(
            rows,
            colWidths=[
                25 * mm,
                110 * mm,
                55 * mm,
                55 * mm,
            ],
            repeatRows=1,
        )

        detail_table.setStyle(
            _table_style()
        )

        story.append(detail_table)

        # Compact spacing instead of a page break after every column.
        if column_index < len(columns) - 1:
            story.append(
                Spacer(
                    1,
                    5,
                )
            )


# ============================================================================
# MULTIVARIATE REPORT
# ============================================================================

def _multivariate_report(
    story,
    detection: dict[str, Any],
    dataframe,
    styles,
    dataset_id: str,
):
    from app.api.automatic_discovery import (
        feature_contribution,
    )

    # ------------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------------

    story.append(
        Paragraph(
            "Multivariate Detection Summary",
            styles["SectionCustom"],
        )
    )

    records = detection.get(
        "records",
        [],
    )

    labels = np.asarray(
        [
            1
            if str(
                record.get(
                    "status",
                    "",
                )
            ).lower()
            == "anomaly"
            else 0
            for record in records
        ],
        dtype=np.uint8,
    )

    total = len(labels)

    anomaly_count = int(
        labels.sum()
    )

    percentage = (
        100.0 * anomaly_count / total
        if total
        else 0.0
    )

    summary_rows = [
        [
            "Total Records",
            "No. of Anomalies",
            "% of Anomalies",
        ],
        [
            _paragraph(
                total,
                styles,
                centered=True,
            ),
            _paragraph(
                anomaly_count,
                styles,
                centered=True,
            ),
            _paragraph(
                f"{percentage:.4f}%",
                styles,
                centered=True,
            ),
        ],
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[
            80 * mm,
            80 * mm,
            80 * mm,
        ],
        repeatRows=1,
    )

    summary_table.setStyle(
        _table_style()
    )

    story.append(summary_table)
    story.append(
        Spacer(
            1,
            5,
        )
    )

    _benchmark_section(
        story,
        detection,
        styles,
    )

    story.append(
        Paragraph(
            "Detected Anomaly Records",
            styles["SectionCustom"],
        )
    )

    columns = list(
        detection.get(
            "columns",
            [],
        )
    )

    # ------------------------------------------------------------------------
    # TABLE HEADER
    # ------------------------------------------------------------------------

    header = [
        "Record"
    ]

    header.extend(
        str(column)
        for column in columns
    )

    header.extend(
        [
            "Anomaly Score",
            "Threshold",
            "Status",
            "Top 3 Contributing Features",
        ]
    )

    rows = [header]

    # ------------------------------------------------------------------------
    # ONLY ANOMALY RECORDS
    # ------------------------------------------------------------------------

    for index, record in enumerate(records):

        status = str(
            record.get(
                "status",
                "",
            )
        )

        if status.lower() != "anomaly":
            continue

        record_number = index + 1

        # ------------------------------------------------------------
        # ACTUAL FEATURE VALUES FROM DATAFRAME
        # ------------------------------------------------------------

        feature_values = []

        for column in columns:

            try:
                value = dataframe.iloc[index][column]
            except (IndexError, KeyError):
                value = None

            feature_values.append(
                _paragraph(
                    value,
                    styles,
                )
            )

        # ------------------------------------------------------------
        # EXISTING FEATURE CONTRIBUTION LOGIC
        # ONLY TOP 3 ARE DISPLAYED
        # ------------------------------------------------------------

        contribution_text = "Not available"

        try:

            contribution_response = (
                feature_contribution(
                    dataset_id,
                    record_number,
                    top_n=3,
                )
            )

            contribution_rows = (
                contribution_response.get(
                    "top_contributing_attributes",
                    [],
                )
            )

            contribution_parts = []

            for item in contribution_rows[:3]:

                feature = _safe_text(
                    item.get(
                        "feature"
                    )
                )

                try:
                    percentage_value = float(
                        item.get(
                            "contribution_percent",
                            item.get(
                                "contribution_percentage",
                                0.0,
                            ),
                        )
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    percentage_value = 0.0

                contribution_parts.append(
                    (
                        f"<b>{feature}</b>: "
                        f"{percentage_value:.2f}%"
                    )
                )

            if contribution_parts:
                contribution_text = (
                    "<br/>".join(
                        contribution_parts
                    )
                )

        except Exception:
            contribution_text = "Not available"

        # ------------------------------------------------------------
        # BUILD ROW
        # ------------------------------------------------------------

        row = [
            _paragraph(
                record_number,
                styles,
                centered=True,
            )
        ]

        row.extend(
            feature_values
        )

        row.extend(
            [
                _paragraph(
                    _fmt(
                        record.get(
                            "anomaly_score"
                        ),
                        8,
                    ),
                    styles,
                ),
                _paragraph(
                    record.get(
                        "threshold"
                    ),
                    styles,
                ),
                _paragraph(
                    status,
                    styles,
                    centered=True,
                ),
                Paragraph(
                    contribution_text,
                    styles["CellCustom"],
                ),
            ]
        )

        rows.append(row)

    # ------------------------------------------------------------------------
    # NO ANOMALIES
    # ------------------------------------------------------------------------

    if len(rows) == 1:

        empty_row = [
            _paragraph(
                "—",
                styles,
                centered=True,
            )
        ]

        empty_row.extend(
            _paragraph(
                "—",
                styles,
                centered=True,
            )
            for _ in columns
        )

        empty_row.extend(
            [
                _paragraph(
                    "No anomaly records detected.",
                    styles,
                ),
                _paragraph(
                    "—",
                    styles,
                    centered=True,
                ),
                _paragraph(
                    "—",
                    styles,
                    centered=True,
                ),
                _paragraph(
                    "—",
                    styles,
                ),
            ]
        )

        rows.append(
            empty_row
        )

    # ------------------------------------------------------------------------
    # COMPACT DYNAMIC WIDTHS
    #
    # Landscape A4 usable width:
    # 297 mm - 12 mm left - 12 mm right = 273 mm
    #
    # The complete table is always constrained to that width.
    # ------------------------------------------------------------------------

    usable_width = 273.0

    fixed_widths = {
        "record": 13.0,
        "score": 25.0,
        "threshold": 25.0,
        "status": 19.0,
        "contribution": 45.0,
    }

    fixed_total = sum(
        fixed_widths.values()
    )

    remaining_width = (
        usable_width - fixed_total
    )

    feature_count = len(columns)

    if feature_count > 0:
        feature_width = (
            remaining_width / feature_count
        )
    else:
        feature_width = remaining_width

    # Keep the table within the page even when there
    # are many selected attributes.
    feature_width = max(
        10.0,
        feature_width,
    )

    col_widths = [
        fixed_widths["record"]
    ]

    col_widths.extend(
        feature_width
        for _ in columns
    )

    col_widths.extend(
        [
            fixed_widths["score"],
            fixed_widths["threshold"],
            fixed_widths["status"],
            fixed_widths["contribution"],
        ]
    )

    # Final safety normalization so total width is never
    # larger than the usable landscape A4 width.
    total_width = sum(
        col_widths
    )

    if total_width > usable_width:

        scale = (
            usable_width / total_width
        )

        col_widths = [
            width * scale
            for width in col_widths
        ]

    detail_table = Table(
        rows,
        colWidths=[
            width * mm
            for width in col_widths
        ],
        repeatRows=1,
        hAlign="LEFT",
    )

    detail_table.setStyle(
        _table_style()
    )

    story.append(
        detail_table
    )


# ============================================================================
# MAIN REPORT GENERATOR
# ============================================================================

def generate_report(
    dataset_id: str,
    session: Any,
    detection: dict[str, Any],
) -> bytes:

    dataframe = detection.get(
        "dataframe"
    )

    if dataframe is None:
        dataframe = getattr(
            session,
            "preprocessed_df",
            None,
        )

    if dataframe is None:
        raise ValueError(
            "Preprocessed dataset is not available "
            "for report generation."
        )

    columns = list(
        detection.get(
            "columns"
        )
        or getattr(
            session,
            "selected_columns",
            None,
        )
        or []
    )

    if not columns:
        raise ValueError(
            "No selected columns are available "
            "for report generation."
        )

    dataset_name = _dataset_name(
        session,
        dataset_id,
    )

    approach = detection.get(
        "approach"
    )

    if approach not in {
        "univariate",
        "multivariate",
    }:
        raise ValueError(
            "Unsupported detection approach."
        )

    # ========================================================================
    # PDF
    # ========================================================================

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=(
            "Machine Learning "
            "Anomaly Detection Report"
        ),
        author="ANOMXENSE",
    )

    styles = _styles()

    story = []

    # ========================================================================
    # TITLE
    # ========================================================================

    if approach == "univariate":
        title = (
            "UNIVARIATE MACHINE LEARNING "
            "BENCHMARKING REPORT"
        )
    else:
        title = (
            "MULTIVARIATE MACHINE LEARNING "
            "BENCHMARKING REPORT"
        )

    story.append(
        Paragraph(
            title,
            styles["ReportTitleCustom"],
        )
    )

    story.append(
        Paragraph(
            "Machine Learning Anomaly Detection Report",
            styles["ReportSubtitleCustom"],
        )
    )

    # ========================================================================
    # HEADER
    # ========================================================================

    story.append(
        _header_table(
            dataset_name,
            dataframe,
            columns,
            detection,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            6,
        )
    )

    # ========================================================================
    # APPROACH-SPECIFIC REPORT
    # ========================================================================

    if approach == "univariate":

        _univariate_report(
            story,
            detection,
            dataframe,
            columns,
            styles,
        )

    elif approach == "multivariate":

        _multivariate_report(
            story,
            detection,
            dataframe,
            styles,
            dataset_id,
        )

    # ========================================================================
    # BUILD
    # ========================================================================

    doc.build(
        story
    )

    return buffer.getvalue()
    