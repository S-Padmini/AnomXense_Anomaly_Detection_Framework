from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.automatic_discovery_store import get_state


def _safe_text(value: Any) -> str:
    if value is None:
        return "—"

    text = str(value)

    if text.lower() in {"nan", "nat", "none"}:
        return "—"

    return text


def _get_dataset_filename(session: Any, detection: dict[str, Any]) -> str:
    candidates = [
        getattr(session, "filename", None),
        getattr(session, "file_name", None),
        getattr(session, "original_filename", None),
        getattr(session, "original_file_name", None),
        getattr(session, "dataset_filename", None),
        getattr(session, "dataset_name", None),
    ]

    for value in candidates:
        if value:
            return Path(str(value)).name

    return "Dataset"


def _header_value(
    detection: dict[str, Any],
    session: Any,
    key: str,
    default: Any = "—",
) -> Any:
    if key == "dataset_filename":
        return _get_dataset_filename(session, detection)

    return detection.get(key, default)


def _styles():
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontSize=6.5,
            leading=8,
        ),
        "cell_center": ParagraphStyle(
            "CellCenter",
            parent=styles["Normal"],
            fontSize=6.5,
            leading=8,
            alignment=TA_CENTER,
        ),
    }


def _p(value: Any, style):
    return Paragraph(
        _safe_text(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        style,
    )


def _styled_table(
    data: list[list[Any]],
    *,
    widths: list[float] | None = None,
    repeat_rows: int = 1,
):
    table = Table(
        data,
        colWidths=widths,
        repeatRows=repeat_rows,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0f172a"),
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
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f8fafc"),
                    ],
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


def _build_header(
    detection: dict[str, Any],
    session: Any,
    approach: str,
):
    styles = _styles()

    dataset = detection.get("dataframe")

    total_records = (
        len(dataset)
        if dataset is not None
        else int(detection.get("total_records_processed", 0))
    )

    columns = list(detection.get("columns", []))

    score_method = detection.get(
        "score_method",
        "best_score",
    )

    models = [
        str(model.get("model"))
        for model in detection.get("models", [])
    ]

    if score_method == "combined_score":
        detection_method = "Combined Score"
        model_used = ", ".join(models) if models else "Ensemble"
    else:
        detection_method = "Best Score"
        model_used = (
            detection.get("selected_model")
            or (models[0] if models else "—")
        )

    variability = (
        "Univariate"
        if approach == "univariate"
        else "Multivariate"
    )

    rows = [
        [
            _p("Dataset Filename", styles["cell"]),
            _p(
                _get_dataset_filename(session, detection),
                styles["cell"],
            ),
        ],
        [
            _p("No. of Records", styles["cell"]),
            _p(total_records, styles["cell"]),
        ],
        [
            _p("No. of Attributes", styles["cell"]),
            _p(len(columns), styles["cell"]),
        ],
        [
            _p("Approach Used", styles["cell"]),
            _p(
                "Machine Learning Benchmarking Approach",
                styles["cell"],
            ),
        ],
        [
            _p("Detection Method", styles["cell"]),
            _p(detection_method, styles["cell"]),
        ],
        [
            _p("Model Used", styles["cell"]),
            _p(model_used, styles["cell"]),
        ],
        [
            _p("Variability", styles["cell"]),
            _p(variability, styles["cell"]),
        ],
    ]

    table = Table(
        rows,
        colWidths=[
            48 * mm,
            112 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#cbd5e1"),
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
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
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
            ]
        )
    )

    return table


def _build_univariate_report(
    detection: dict[str, Any],
    session: Any,
):
    from app.phases.phase6.automatic_discovery import (
        _build_column_summaries,
        _column_ensemble_view,
    )

    styles = _styles()
    dataframe = detection["dataframe"]

    story = []

    story.append(
        Paragraph(
            "UNIVARIATE MACHINE LEARNING BENCHMARKING REPORT",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Machine Learning Anomaly Detection Report",
            styles["subtitle"],
        )
    )

    story.append(
        _build_header(
            detection,
            session,
            "univariate",
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Best Score / Combined Score",
            styles["section"],
        )
    )

    models = detection.get("models", [])

    if detection.get("score_method") == "combined_score":
        selected_text = ", ".join(
            str(model.get("model"))
            for model in models
        )
    else:
        selected_text = (
            detection.get("selected_model")
            or (
                str(models[0].get("model"))
                if models
                else "—"
            )
        )

    best_score_table = _styled_table(
        [
            [
                _p("Detection Method", styles["cell"]),
                _p("Selected Model(s)", styles["cell"]),
            ],
            [
                _p(
                    (
                        "Combined Score"
                        if detection.get("score_method")
                        == "combined_score"
                        else "Best Score"
                    ),
                    styles["cell"],
                ),
                _p(
                    selected_text,
                    styles["cell"],
                ),
            ],
        ],
        widths=[
            55 * mm,
            105 * mm,
        ],
    )

    story.append(best_score_table)

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Combined Score Models",
            styles["section"],
        )
    )

    combined_rows = [
        [
            _p("Rank", styles["cell"]),
            _p("Model", styles["cell"]),
            _p(
                "Benchmark Combined Score",
                styles["cell"],
            ),
            _p("Ensemble Weight", styles["cell"]),
        ]
    ]

    for rank, model in enumerate(models[:3], start=1):
        combined_rows.append(
            [
                _p(rank, styles["cell_center"]),
                _p(
                    model.get("model"),
                    styles["cell"],
                ),
                _p(
                    model.get(
                        "benchmark_combined_score"
                    ),
                    styles["cell"],
                ),
                _p(
                    model.get("weight"),
                    styles["cell"],
                ),
            ]
        )

    story.append(
        _styled_table(
            combined_rows,
            widths=[
                18 * mm,
                55 * mm,
                48 * mm,
                39 * mm,
            ],
        )
    )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Detection Summary",
            styles["section"],
        )
    )

    summary_rows = [
        [
            _p("Column Name", styles["cell"]),
            _p(
                "No. of Anomalies",
                styles["cell"],
            ),
            _p(
                "% of Anomalies",
                styles["cell"],
            ),
        ]
    ]

    summaries = _build_column_summaries(detection)

    for item in summaries:
        summary_rows.append(
            [
                _p(
                    item["column"],
                    styles["cell"],
                ),
                _p(
                    item["anomaly_records"],
                    styles["cell_center"],
                ),
                _p(
                    f'{item["anomaly_rate_percent"]:.4f}%',
                    styles["cell_center"],
                ),
            ]
        )

    story.append(
        _styled_table(
            summary_rows,
            widths=[
                90 * mm,
                35 * mm,
                35 * mm,
            ],
        )
    )

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Detailed Results",
            styles["section"],
        )
    )

    for column in detection.get("columns", []):
        story.append(
            Paragraph(
                f"Column: {_safe_text(column)}",
                styles["section"],
            )
        )

        scores, labels, threshold, _ = (
            _column_ensemble_view(
                detection,
                column,
            )
        )

        rows = [
            [
                _p("Record", styles["cell"]),
                _p(
                    f"Value of {column}",
                    styles["cell"],
                ),
                _p("Score", styles["cell"]),
                _p("Threshold", styles["cell"]),
            ]
        ]

        for index in range(len(scores)):
            value = dataframe.iloc[index][column]

            rows.append(
                [
                    _p(
                        index + 1,
                        styles["cell_center"],
                    ),
                    _p(
                        value,
                        styles["cell"],
                    ),
                    _p(
                        f"{float(scores[index]):.8f}",
                        styles["cell"],
                    ),
                    _p(
                        f"{float(threshold):.8f}",
                        styles["cell"],
                    ),
                ]
            )

        story.append(
            _styled_table(
                rows,
                widths=[
                    22 * mm,
                    75 * mm,
                    42 * mm,
                    42 * mm,
                ],
            )
        )

        story.append(Spacer(1, 10))

    return story


def _build_multivariate_report(
    detection: dict[str, Any],
    session: Any,
    dataset_id: str,
):
    from app.phases.phase6.automatic_discovery import (
        feature_contribution,
    )

    styles = _styles()

    story = []

    story.append(
        Paragraph(
            "MULTIVARIATE MACHINE LEARNING BENCHMARKING REPORT",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Machine Learning Anomaly Detection Report",
            styles["subtitle"],
        )
    )

    story.append(
        _build_header(
            detection,
            session,
            "multivariate",
        )
    )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Detection Summary",
            styles["section"],
        )
    )

    total_records = int(
        detection.get(
            "total_records_processed",
            len(detection.get("records", [])),
        )
    )

    anomaly_count = int(
        detection.get(
            "anomaly_records_count",
            0,
        )
    )

    anomaly_percentage = (
        100.0 * anomaly_count / total_records
        if total_records
        else 0.0
    )

    summary_rows = [
        [
            _p(
                "Total Records",
                styles["cell"],
            ),
            _p(
                "No. of Anomalies",
                styles["cell"],
            ),
            _p(
                "% of Anomalies",
                styles["cell"],
            ),
        ],
        [
            _p(
                total_records,
                styles["cell_center"],
            ),
            _p(
                anomaly_count,
                styles["cell_center"],
            ),
            _p(
                f"{anomaly_percentage:.4f}%",
                styles["cell_center"],
            ),
        ],
    ]

    story.append(
        _styled_table(
            summary_rows,
            widths=[
                53 * mm,
                53 * mm,
                53 * mm,
            ],
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "Detected Anomaly Records",
            styles["section"],
        )
    )

    dataframe = detection["dataframe"]
    columns = list(detection.get("columns", []))

    anomaly_records = [
        record
        for record in detection.get("records", [])
        if str(record.get("status", "")).lower()
        == "anomaly"
    ]

    rows = [
        [
            _p("Record", styles["cell"]),
            _p("Feature Values", styles["cell"]),
            _p("Score", styles["cell"]),
            _p("Threshold", styles["cell"]),
            _p("Status", styles["cell"]),
            _p(
                "Feature Contribution",
                styles["cell"],
            ),
        ]
    ]

    for record in anomaly_records:
        record_number = int(
            record["record_number"]
        )

        values = record.get("values", {})

        feature_values = "<br/>".join(
            (
                f"<b>{_safe_text(column)}</b>: "
                f"{_safe_text(values.get(column))}"
            )
            for column in columns
        )

        contribution_text = "—"

        try:
            contribution_response = feature_contribution(
                dataset_id,
                record_number,
                top_n=max(1, len(columns)),
            )

            contribution_rows = (
                contribution_response.get(
                    "top_contributing_attributes",
                    [],
                )
            )

            contribution_parts = []

            for item in contribution_rows:
                contribution_parts.append(
                    (
                        f"<b>{_safe_text(item.get('feature'))}</b>: "
                        f"{float(item.get('contribution_percent', 0.0)):.2f}%"
                    )
                )

            if contribution_parts:
                contribution_text = "<br/>".join(
                    contribution_parts
                )

        except (HTTPException, ValueError, KeyError, TypeError):
            contribution_text = "Not available"

        rows.append(
            [
                _p(
                    record_number,
                    styles["cell_center"],
                ),
                Paragraph(
                    feature_values,
                    styles["cell"],
                ),
                _p(
                    f"{float(record.get('anomaly_score', 0.0)):.8f}",
                    styles["cell"],
                ),
                _p(
                    record.get("threshold"),
                    styles["cell"],
                ),
                _p(
                    record.get("status"),
                    styles["cell_center"],
                ),
                Paragraph(
                    contribution_text,
                    styles["cell"],
                ),
            ]
        )

    story.append(
        _styled_table(
            rows,
            widths=[
                16 * mm,
                55 * mm,
                30 * mm,
                30 * mm,
                22 * mm,
                42 * mm,
            ],
        )
    )

    return story


def generate_report(
    dataset_id: str,
):
    from app.phases.phase6.automatic_discovery import (
        get_session,
        get_detection,
    )

    session = get_session(dataset_id)
    detection = get_detection(dataset_id)

    approach = detection.get("approach")

    if approach not in {
        "univariate",
        "multivariate",
    }:
        raise HTTPException(
            status_code=422,
            detail="Unsupported detection approach.",
        )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Machine Learning Anomaly Detection Report",
        author="ANOMXENSE",
    )

    if approach == "univariate":
        story = _build_univariate_report(
            detection,
            session,
        )
    else:
        story = _build_multivariate_report(
            detection,
            session,
            dataset_id,
        )

    document.build(story)

    buffer.seek(0)

    filename = _get_dataset_filename(
        session,
        detection,
    )

    safe_stem = Path(filename).stem or "dataset"

    report_name = (
        f"{safe_stem}_"
        f"{approach}_"
        f"machine_learning_benchmarking_report.pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{report_name}"'
            )
        },
    )