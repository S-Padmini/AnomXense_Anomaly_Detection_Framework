import { useEffect, useRef, useState } from "react";

import FileUpload from "./components/FileUpload";

import {
  confirmSelection,
  getColumnDetails,
  getPreview,
  getPreprocessingInspection,
  saveSelection,
  preprocessDataset,
  runStatisticalAnalysis,
  uploadDataset,
} from "./services/api";

import "./App.css";

/* =========================================================
   ANALYSIS TYPES
   ========================================================= */

const ANALYSES = [
  ["overview", "1. Dataset Size & Dimensionality"],
  ["types", "2. Data Type & Feature Composition"],
  ["distribution", "3. Distribution Analysis"],
  ["extreme", "4. Extreme Value Analysis"],
  ["scale", "5. Feature Scale Analysis"],
  ["correlation", "6. Correlation Analysis"],
  ["cluster", "7. Cluster Structure Analysis"],
  ["density", "8. Local Density & Neighborhood Analysis"],
  ["temporal", "9. Temporal Structure Analysis"],
  ["timeseries", "10. Time-Series Pattern Analysis"],
];

/* =========================================================
   PHASES
   ========================================================= */

const PHASES = [
  ["01", "Dataset Analysis"],
  ["02", "Column Selection"],
  ["03", "Preprocessing & Analysis"],
  ["04", "Detection Configuration"],
  ["05", "Model Recommendation"],
  ["06", "Training"],
  ["07", "Visualization"],
];

/* =========================================================
   MAIN APP
   ========================================================= */

function App() {
  const [summary, setSummary] = useState(null);
  const [file, setFile] = useState(null);

  const [activePhase, setActivePhase] = useState(1);

  const [selectedColumns, setSelectedColumns] = useState([]);
  const [confirmed, setConfirmed] = useState(false);
  const [confirmationOpen, setConfirmationOpen] = useState(false);

  const [selectedDetail, setSelectedDetail] = useState(null);
  const [infoColumn, setInfoColumn] = useState(null);

  const [loading, setLoading] = useState(false);
  const [phase3Loading, setPhase3Loading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  const [error, setError] = useState("");

  const [inspection, setInspection] = useState(null);
  const [inspectionLoading, setInspectionLoading] = useState(false);

  const [inspectionData, setInspectionData] = useState(null);
  const [preprocessResult, setPreprocessResult] = useState(null);

  const [preview, setPreview] = useState(null);
  const [previewPage, setPreviewPage] = useState(1);

  const [analysis, setAnalysis] = useState(null);

  const [openSections, setOpenSections] = useState({
    overview: true,
  });

  const datasetId = summary?.dataset_id;

  /* =========================================================
     COLUMN INFORMATION OUTSIDE CLICK
  ========================================================= */

  useEffect(() => {
    if (!infoColumn) {
      return;
    }

    function handleOutsideClick(event) {
      if (!event.target.closest(".column-row")) {
        setInfoColumn(null);
        setSelectedDetail(null);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);

    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [infoColumn]);

  /* =========================================================
     RESET
     ========================================================= */

  function resetForNewFile() {
    setSummary(null);
    setSelectedColumns([]);
    setConfirmed(false);
    setConfirmationOpen(false);

    setSelectedDetail(null);
    setInfoColumn(null);

    setActivePhase(1);

    setInspection(null);
    setInspectionData(null);
    setInspectionLoading(false);

    setPreprocessResult(null);

    setPreview(null);
    setPreviewPage(1);

    setAnalysis(null);

    setOpenSections({
      overview: true,
    });

    setError("");
  }

  /* =========================================================
     FILE UPLOAD
     ========================================================= */

  async function handleFileSelected(nextFile) {
    resetForNewFile();

    setFile(nextFile);
    setLoading(true);
    setError("");

    try {
      const result = await uploadDataset(nextFile);

      setSummary(result);

      setSelectedColumns(result.all_column_names || []);

      const firstColumn = result.all_column_names?.[0];

      if (firstColumn) {
        const details = result.column_details?.[firstColumn];

        if (details) {
          setSelectedDetail({
            name: firstColumn,
            ...details,
          });
        }
      }
    } catch (err) {
      setError(
        err?.message || "Unable to analyze dataset."
      );
    } finally {
      setLoading(false);
    }
  }

  /* =========================================================
     COLUMN DETAILS
     ========================================================= */

  async function chooseColumn(column) {
    /*
      Same icon = close. Another icon = switch the open details.
    */
    if (infoColumn === column) {
      setInfoColumn(null);
      setSelectedDetail(null);
      return;
    }

    setInfoColumn(column);

    const cachedDetails =
      summary?.column_details?.[column];

    setSelectedDetail({
      name: column,
      ...(cachedDetails || {}),
    });

    if (!datasetId) {
      return;
    }

    try {
      const result = await getColumnDetails(
        datasetId,
        column
      );

      setSelectedDetail((current) => {
        if (!current || current.name !== column) {
          return current;
        }

        return {
          ...current,
          ...(result?.details || {}),
        };
      });
    } catch (err) {
      setError(
        err?.message ||
          "Unable to load column details."
      );
    }
  }

  function closeColumnInfo() {
    setInfoColumn(null);
  }

  /* =========================================================
     TOGGLE COLUMN
     ========================================================= */

  function toggleColumn(column) {
    setSelectedColumns((current) => {
      if (current.includes(column)) {
        const next = current.filter(
          (item) => item !== column
        );

        if (selectedDetail?.name === column) {
          setSelectedDetail(null);
          setInfoColumn(null);
        }

        return next;
      }

      return [...current, column];
    });

    setConfirmed(false);
    setConfirmationOpen(false);

    setPreprocessResult(null);
    setPreview(null);
    setAnalysis(null);

    setInspection(null);
    setInspectionData(null);
  }

  /* =========================================================
     CONFIRM COLUMN SELECTION
     ========================================================= */

  async function handleConfirmSelection() {
    if (
      !datasetId ||
      selectedColumns.length === 0
    ) {
      return;
    }

    setPhase3Loading(true);
    setError("");

    try {
      await saveSelection(
        datasetId,
        selectedColumns
      );

      await confirmSelection(datasetId);

      setConfirmed(true);
      setConfirmationOpen(true);
    } catch (err) {
      setError(
        err?.message || "Unable to confirm selection."
      );
    } finally {
      setPhase3Loading(false);
    }
  }

  /* =========================================================
     PROCEED TO PHASE 3
     ========================================================= */

  function proceedToPreprocessing() {
    setConfirmationOpen(false);
    setActivePhase(3);
  }

  function editSelection() {
    setConfirmationOpen(false);
    setActivePhase(2);
  }

  /* =========================================================
     OPEN PHASE 3
     ========================================================= */

  async function openPhase3() {
    if (
      !datasetId ||
      (!confirmed && !preprocessResult)
    ) {
      return;
    }

    setActivePhase(3);
    setPhase3Loading(true);
    setError("");

    try {
      const inspectionResult =
        await getPreprocessingInspection(
          datasetId
        );

      setInspectionData(inspectionResult);

      if (preprocessResult) {
        const previewResult = await getPreview(
          datasetId,
          previewPage,
          10
        );

        setPreview(previewResult);
      }
    } catch (err) {
      setError(
        err?.message ||
          "Unable to load preprocessing analysis."
      );
    } finally {
      setPhase3Loading(false);
    }
  }

  /* =========================================================
     PREPROCESS DATASET
     ========================================================= */

  async function handlePreprocess() {
    if (
      !datasetId ||
      selectedColumns.length === 0 ||
      !confirmed
    ) {
      return;
    }

    setPhase3Loading(true);
    setError("");

    try {
      const result = await preprocessDataset(
        datasetId,
        selectedColumns
      );

      setPreprocessResult(result);
      setPreviewPage(1);

      const [
        inspectionResult,
        previewResult,
      ] = await Promise.all([
        getPreprocessingInspection(datasetId),
        getPreview(datasetId, 1, 10),
      ]);

      setInspectionData(inspectionResult);
      setPreview(previewResult);

      setAnalysis(null);

      setOpenSections({
        overview: true,
      });
    } catch (err) {
      setError(
        err?.message ||
          "Unable to preprocess dataset."
      );
    } finally {
      setPhase3Loading(false);
    }
  }

  /* =========================================================
     DATASET PREVIEW PAGINATION
     ========================================================= */

  async function changePreviewPage(page) {
    if (
      !datasetId ||
      !preprocessResult
    ) {
      return;
    }

    setPhase3Loading(true);
    setError("");

    try {
      const result = await getPreview(
        datasetId,
        page,
        10
      );

      setPreview(result);
      setPreviewPage(result?.page || page);
    } catch (err) {
      setError(
        err?.message ||
          "Unable to load dataset page."
      );
    } finally {
      setPhase3Loading(false);
    }
  }

  /* =========================================================
     STATISTICAL ANALYSIS
     ========================================================= */

  async function handleRunAnalysis() {
    if (
      !datasetId ||
      !preprocessResult
    ) {
      return;
    }

    setAnalysisLoading(true);
    setError("");

    try {
      const result =
        await runStatisticalAnalysis(
          datasetId,
          selectedColumns
        );

      setAnalysis(result);

      setOpenSections({
        overview: true,
      });
    } catch (err) {
      setError(
        err?.message ||
          "Unable to calculate statistical analysis."
      );
    } finally {
      setAnalysisLoading(false);
    }
  }

  /* =========================================================
     RECORD INSPECTION
     ========================================================= */

  async function inspect(payload) {
    setInspection(payload);
    setInspectionLoading(true);
    setError("");

    try {
      let focusedRecords = [];

      if (payload.kind === "missing-column") {
        const columnStats =
          inspectionData?.columns?.find(
            (item) =>
              item.column === payload.column
          );

        focusedRecords =
          columnStats?.missing_records || [];
      } else if (
        payload.kind === "duplicate-column"
      ) {
        const columnStats =
          inspectionData?.columns?.find(
            (item) =>
              item.column === payload.column
          );

        focusedRecords =
          columnStats?.duplicate_records || [];
      } else if (
        payload.kind === "missing-total"
      ) {
        const allMissingRecords =
          inspectionData?.allMissingRecords || [];

        focusedRecords =
          allMissingRecords.flatMap(
            (item) =>
              (item.records || []).map(
                (record) => ({
                  ...record,
                  column: item.column,
                })
              )
          );
      } else if (
        payload.kind === "duplicate-total"
      ) {
        focusedRecords =
          inspectionData?.allDuplicateRecords || [];
      }

      setInspectionData((current) => ({
        ...(current || {}),
        focused: focusedRecords,
      }));
    } catch (err) {
      setError(
        err?.message ||
          "Unable to inspect records."
      );
    } finally {
      setInspectionLoading(false);
    }
  }

  /* =========================================================
     SIDEBAR NAVIGATION
     ========================================================= */

  function navigate(phase) {
    if (!summary) {
      return;
    }

    if (phase === 1) {
      setActivePhase(1);
      return;
    }

    if (phase === 2) {
      setActivePhase(2);
      return;
    }

    if (
      phase === 3 &&
      (confirmed || preprocessResult)
    ) {
      openPhase3();
    }
  }

  /* =========================================================
     RENDER
     ========================================================= */

  return (
    <div className="app-shell">
      <Sidebar
        activePhase={activePhase}
        summary={summary}
        confirmed={
          confirmed || Boolean(preprocessResult)
        }
        onNavigate={navigate}
      />

      <div className="app-content">
        <header className="top-header">
          <div>
            <p className="eyebrow">
              INTELLIGENT ANOMALY INSIGHTS
            </p>

            <h1>
              Smart Anomaly Detection Framework
            </h1>

            <p className="subtitle">
              Analyze, preprocess and understand
              the selected dataset before anomaly
              detection.
            </p>
          </div>

          {file && (
            <div className="header-file">
              {file.name}
            </div>
          )}
        </header>

        <main className="main-content">
          <FileUpload
            onFileSelected={handleFileSelected}
            disabled={loading}
          />

          {loading && (
            <StatusCard
              text="Processing dataset"
              detail="Preparing the selected data and analysis..."
            />
          )}

          {error && (
            <div className="error-card">
              <strong>
                Unable to complete the request
              </strong>

              <p>{error}</p>

              <button
                type="button"
                className="text-button"
                onClick={() => setError("")}
              >
                Dismiss
              </button>
            </div>
          )}

          {summary && activePhase === 1 && (
            <Phase1
              summary={summary}
              onNext={() => setActivePhase(2)}
            />
          )}

          {summary && activePhase === 2 && (
            <Phase2
              summary={summary}
              selectedColumns={selectedColumns}
              selectedDetail={selectedDetail}
              infoColumn={infoColumn}
              onToggle={toggleColumn}
              onInfo={chooseColumn}
              onCloseInfo={closeColumnInfo}
              onConfirm={handleConfirmSelection}
              confirming={phase3Loading}
            />
          )}

          {summary && activePhase === 3 && (
            <Phase3
              summary={summary}
              selectedColumns={selectedColumns}
              inspectionData={inspectionData}
              preprocessResult={preprocessResult}
              preview={preview}
              previewPage={previewPage}
              phase3Loading={phase3Loading}
              analysis={analysis}
              analysisLoading={analysisLoading}
              openSections={openSections}
              onInspect={inspect}
              onPreprocess={handlePreprocess}
              onEditColumns={() => setActivePhase(2)}
              onPage={changePreviewPage}
              onRunAnalysis={handleRunAnalysis}
              onToggleAnalysis={(key) =>
                setOpenSections((current) => ({
                  ...current,
                  [key]: !current[key],
                }))
              }
            />
          )}
        </main>
      </div>

      {confirmationOpen && (
        <ConfirmationModal
          count={selectedColumns.length}
          onProceed={proceedToPreprocessing}
          onEdit={editSelection}
        />
      )}

      {inspection && (
        <InspectionModal
          payload={inspection}
          data={inspectionData?.focused || null}
          loading={inspectionLoading}
          onClose={() => setInspection(null)}
        />
      )}
    </div>
  );
}

/* =========================================================
   SIDEBAR
   ========================================================= */

function Sidebar({
  activePhase,
  summary,
  confirmed,
  onNavigate,
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          IA
        </div>

        <div>
          <div>Intelligent</div>
          <div>Anomaly Insights</div>
        </div>
      </div>

      <div className="sidebar-divider" />

      <p className="sidebar-label">
        WORKFLOW
      </p>

      <nav>
        {PHASES.map(([number, label], index) => {
          const phase = index + 1;

          const locked =
            !summary ||
            phase > 3 ||
            (phase === 3 && !confirmed);

          const isActive =
            activePhase === phase;

          let className = "phase-nav-item";

          if (isActive) {
            className += " active";
          }

          if (locked) {
            className += " locked";
          }

          return (
            <button
              key={number}
              type="button"
              className={className}
              disabled={locked}
              onClick={() => onNavigate(phase)}
            >
              <span className="phase-number">
                {number}
              </span>

              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />

        <span>
          Analysis workspace
        </span>
      </div>
    </aside>
  );
}

/* =========================================================
   SECTION HEADING
   ========================================================= */

function SectionHeading({
  phase,
  title,
  subtitle,
  badge,
}) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">
          {phase}
        </p>

        <h2>{title}</h2>

        <p className="section-subtitle">
          {subtitle}
        </p>
      </div>

      {badge && (
        <div className="status-badge">
          {badge}
        </div>
      )}
    </div>
  );
}

/* =========================================================
   PHASE 1
   ========================================================= */

function Phase1({
  summary,
  onNext,
}) {
  const fileSize = Number(
    summary?.file_size_mb || 0
  ).toFixed(2);

  const cards = [
    [
      "Rows",
      summary?.rows,
      "Total number of records in the uploaded dataset.",
      null,
    ],
    [
      "Columns",
      summary?.columns,
      "Total number of columns detected.",
      null,
    ],
    [
      "File Size",
      fileSize + " MB",
      "Size of the uploaded file.",
      null,
    ],
    [
      "Numeric",
      summary?.numeric,
      "Numerical columns.",
      summary?.numeric_column_names,
    ],
    [
      "Categorical",
      summary?.categorical,
      "Categorical columns.",
      summary?.categorical_column_names,
    ],
    [
      "Date / Time",
      summary?.datetime,
      "Columns identified as date/time.",
      summary?.datetime_column_names,
    ],
    [
      "Identifiers",
      summary?.identifiers,
      "Columns identified as record/entity identifiers.",
      summary?.identifier_column_names,
    ],
    [
      "Boolean",
      summary?.boolean,
      "Boolean columns.",
      summary?.boolean_column_names,
    ],
    [
      "Null / Empty",
      summary?.null_empty,
      "Columns with no usable values.",
      summary?.null_column_names,
    ],
  ];

  return (
    <section className="workflow-section">
      <SectionHeading
        phase="PHASE 01"
        title="Dataset Analysis"
        subtitle="Overview of the uploaded dataset and automatically identified column characteristics."
        badge="Analysis complete"
      />

      <div className="summary-grid">
        {cards.map(
          ([
            label,
            value,
            description,
            names,
          ]) => (
            <SummaryCard
              key={label}
              label={label}
              value={value}
              description={description}
              names={names}
            />
          )
        )}
      </div>

      {Number(
        summary?.total_missing_values || 0
      ) > 0 && (
        <div className="notice-card">
          <strong>
            {summary.total_missing_values}{" "}
            missing value(s) detected
          </strong>

          <span>
            Affected columns:{" "}
            {(
              summary.columns_with_missing_names ||
              []
            ).join(", ")}
          </span>
        </div>
      )}

      <div className="next-step">
        <div>
          <p className="eyebrow">
            NEXT STEP
          </p>

          <h3>
            Column Selection
          </h3>

          <p>
            Select the columns that should
            participate in preprocessing and
            anomaly detection.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={onNext}
        >
          Continue to Column Selection →
        </button>
      </div>
    </section>
  );
}

/* =========================================================
   SUMMARY CARD
   ========================================================= */

function SummaryCard({
  label,
  value,
  description,
  names,
}) {
  const list = names || [];

  return (
    <div
      className="summary-card"
      tabIndex={0}
    >
      <span className="summary-label">
        {label}
      </span>

      <strong className="summary-value">
        {value ?? 0}
      </strong>

      <div className="card-popover">
        <strong>{label}</strong>

        <p>{description}</p>

        {names !== null &&
          names !== undefined &&
          (
            list.length ? (
              <div className="popover-list">
                {list.map((name) => (
                  <span key={name}>
                    {name}
                  </span>
                ))}
              </div>
            ) : (
              <span className="muted">
                No columns in this category.
              </span>
            )
          )}
      </div>
    </div>
  );
}

/* =========================================================
   PHASE 2
   ========================================================= */

function Phase2({
  summary,
  selectedColumns,
  selectedDetail,
  infoColumn,
  onToggle,
  onInfo,
  onCloseInfo,
  onConfirm,
  confirming,
}) {
  const columns =
    summary?.all_column_names || [];

  const rowRefs = useRef({});

  useEffect(() => {
    if (!infoColumn) {
      return;
    }

    const row = rowRefs.current[infoColumn];

    if (row) {
      window.requestAnimationFrame(() => {
        row.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      });
    }
  }, [infoColumn]);

  return (
    <section className="workflow-section">
      <SectionHeading
        phase="PHASE 02"
        title="Select Columns"
        subtitle="Select the columns that should participate in preprocessing and anomaly detection."
        badge={
          selectedColumns.length +
          " selected"
        }
      />

      <div className="selection-layout">
        <div className="panel column-selection-panel">
          <div className="panel-header">
            <div>
              <h3>
                Available Columns
              </h3>

              <p>
                Choose the columns to carry
                into Phase 3.
              </p>
            </div>

            <span className="count-pill">
              {columns.length} columns
            </span>
          </div>

          <div className="column-list">
            {columns.map(
              (column, index) => {
                const checked =
                  selectedColumns.includes(
                    column
                  );

                const isInfoOpen =
                  infoColumn === column;

                const detail =
                  selectedDetail?.name ===
                  column
                    ? selectedDetail
                    : summary?.column_details?.[
                        column
                      ];

                return (
                  <div
                    ref={(node) => {
                      if (node) {
                        rowRefs.current[column] = node;
                      } else {
                        delete rowRefs.current[column];
                      }
                    }}
                    className={
                      "column-row" +
                      (checked
                        ? " checked"
                        : "") +
                      (isInfoOpen
                        ? " info-open"
                        : "")
                    }
                    key={column}
                  >
                    <div className="column-main-row">
                      <label>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            onToggle(column)
                          }
                        />

                        <span className="column-index">
                          {String(
                            index + 1
                          ).padStart(2, "0")}
                        </span>

                        <strong>
                          {column}
                        </strong>
                      </label>

                      <div className="info-wrapper">
                        <button
                          type="button"
                          className={
                            "info-button" +
                            (isInfoOpen
                              ? " active"
                              : "")
                          }
                          title={
                            isInfoOpen
                              ? "Hide column details"
                              : "Show column details"
                          }
                          aria-expanded={
                            isInfoOpen
                          }
                          aria-label={
                            isInfoOpen
                              ? `Hide details for ${column}`
                              : `Show details for ${column}`
                          }
                          onClick={() =>
                            onInfo(column)
                          }
                        >
                          i
                        </button>
                      </div>
                    </div>

                    {isInfoOpen && (
                      <ColumnDetailsDropdown
                        detail={detail}
                        totalRows={summary?.rows}
                        onClose={onCloseInfo}
                      />
                    )}
                  </div>
                );
              }
            )}
          </div>
        </div>

        <div className="right-stack">
          <div className="panel selected-panel">
            <div className="panel-header">
              <div>
                <h3>
                  Selected Columns
                </h3>

                <p>
                  These columns will be used
                  in Phase 3.
                </p>
              </div>

              <span className="count-pill">
                {selectedColumns.length} /{" "}
                {columns.length}
              </span>
            </div>

            <div className="selected-list">
              {selectedColumns.length ? (
                selectedColumns.map(
                  (column, index) => (
                    <div
                      className="selected-item"
                      key={column}
                    >
                      <span className="column-index">
                        {String(
                          index + 1
                        ).padStart(2, "0")}
                      </span>

                      <span>
                        {column}
                      </span>
                    </div>
                  )
                )
              ) : (
                <div className="empty-state">
                  Select at least one column.
                </div>
              )}
            </div>

            <div className="selection-footer">
              <span>
                <strong>
                  {selectedColumns.length}
                </strong>{" "}
                columns selected
              </span>

              <span>
                {columns.length -
                  selectedColumns.length}{" "}
                excluded
              </span>
            </div>

            <button
              type="button"
              className="primary-button full-width"
              disabled={
                selectedColumns.length === 0 ||
                confirming
              }
              onClick={onConfirm}
            >
              {confirming
                ? "Confirming..."
                : "Confirm Selection ✓"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   COLUMN DETAILS DROPDOWN
   ========================================================= */

function ColumnDetailsDropdown({
  detail,
  totalRows,
  onClose,
}) {
  const rows = Number(totalRows) || 0;

  const missingCount = Number(
    detail?.missing_values ?? 0
  );

  const uniqueCount = Number(
    detail?.unique_values ?? 0
  );

  const missingPercentage =
    rows > 0
      ? (missingCount / rows) * 100
      : null;

  let uniquePercentage =
    rows > 0
      ? (uniqueCount / rows) * 100
      : null;

  if (
    detail?.unique_ratio !== undefined &&
    detail?.unique_ratio !== null &&
    Number.isFinite(Number(detail.unique_ratio))
  ) {
    const ratio = Number(detail.unique_ratio);
    uniquePercentage =
      ratio <= 1 ? ratio * 100 : ratio;
  }

  const formatPercentage = (value) => {
    if (
      value === null ||
      value === undefined ||
      !Number.isFinite(Number(value))
    ) {
      return "—";
    }

    return `${Number(value).toFixed(2)}%`;
  };

  const name = detail?.name || "—";

  return (
    <div
      className="column-details-dropdown"
      role="region"
      aria-label={`Column information for ${name}`}
      onClick={(event) =>
        event.stopPropagation()
      }
    >
      <div className="column-details-dropdown-header">
        <div>
          <span className="popover-eyebrow">
            COLUMN INFORMATION
          </span>

          <h4>{name}</h4>
        </div>

        <button
          type="button"
          className="popover-close"
          onClick={onClose}
          aria-label="Close column information"
        >
          ×
        </button>
      </div>

      <div className="column-details-grid">
        <div className="column-detail-item">
          <span>Column Name</span>
          <strong>{name}</strong>
        </div>

        <div className="column-detail-item">
          <span>Role</span>
          <strong>
            {detail?.role || "—"}
          </strong>
        </div>

        <div className="column-detail-item">
          <span>Data Type</span>
          <strong>
            {detail?.dtype ||
              detail?.data_type ||
              "—"}
          </strong>
        </div>

        <div className="column-detail-item">
          <span>Missing Values %</span>
          <strong>
            {formatPercentage(
              missingPercentage
            )}
          </strong>
        </div>

        <div className="column-detail-item">
          <span>Unique Values %</span>
          <strong>
            {formatPercentage(
              uniquePercentage
            )}
          </strong>
        </div>
      </div>

      <div className="column-detail-description">
        <span>Description</span>

        <p>
          {detail?.description ||
            "No description available."}
        </p>
      </div>
    </div>
  );
}

/* =========================================================
   PHASE 3
   ========================================================= */

function Phase3({
  summary,
  selectedColumns,
  inspectionData,
  preprocessResult,
  preview,
  phase3Loading,
  analysis,
  analysisLoading,
  openSections,
  onInspect,
  onPreprocess,
  onEditColumns,
  onPage,
  onRunAnalysis,
  onToggleAnalysis,
}) {
  const before =
    inspectionData || {
      row_count: summary?.rows,

      columns: selectedColumns.map(
        (column) => ({
          column,

          dtype:
            summary?.column_details?.[
              column
            ]?.dtype || "—",

          missing:
            summary?.column_details?.[
              column
            ]?.missing_values || 0,

          duplicate_values: 0,

          missing_records: [],

          duplicate_records: [],
        })
      ),

      missingTotal:
        selectedColumns.reduce(
          (sum, column) =>
            sum +
            (summary?.column_details?.[
              column
            ]?.missing_values || 0),
          0
        ),

      exactDuplicateRows: 0,
      duplicateValueTotal: 0,
    };

  return (
    <section className="workflow-section">
      <SectionHeading
        phase="PHASE 03"
        title="Preprocessing & Statistical Analysis"
        subtitle="Phase 3 works only on the columns selected in Phase 2. Review detected issues before preprocessing."
        badge={
          selectedColumns.length +
          " selected columns"
        }
      />

      <div className="info-panel">
        <strong>
          Preprocessing Scope
        </strong>

        <span>
          Only missing values and exact
          duplicate records are handled.
          Extreme values are retained for
          anomaly detection.
        </span>
      </div>

      <div className="scope-rule-box">
        <p>
          <strong>
            Duplicate rule:
          </strong>{" "}
          A record is removed only when
          every selected column has exactly
          the same value as another record.
        </p>

        <p>
          <strong>
            Missing values:
          </strong>{" "}
          Numeric columns use mean or median
          according to skewness; categorical
          and boolean columns use mode.
        </p>
      </div>

      <div className="section-block">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">
              3.1 PREPROCESSING
            </p>

            <h3>
              Initial Preprocessing Analysis
            </h3>

            <p className="section-subtitle">
              Every selected column is shown
              with its data type, missing values
              and repeated-value count.
            </p>
          </div>
        </div>

        <div className="analysis-overview-card">
          <div>
            <strong>
              Before Preprocessing
            </strong>

            <span>
              {Number(
                before?.row_count ??
                  before?.rows ??
                  summary?.rows ??
                  0
              ).toLocaleString()}{" "}
              records ×{" "}
              {selectedColumns.length}{" "}
              selected columns
            </span>
          </div>

          <div className="analysis-pill">
            Review only
          </div>
        </div>

        <PreprocessingTable
          stats={before}
          onInspect={onInspect}
        />

        {!preprocessResult && (
          <div className="next-step">
            <div>
              <p className="eyebrow">
                REVIEW COMPLETE?
              </p>

              <h3>
                Preprocess Selected Data
              </h3>

              <p>
                Review missing and repeated
                values first. Only exact duplicate
                records will be removed; extreme
                values are retained.
              </p>
            </div>

            <div className="button-row">
              <button
                type="button"
                className="secondary-button"
                onClick={onEditColumns}
              >
                Edit Column Selection
              </button>

              <button
                type="button"
                className="primary-button"
                disabled={phase3Loading}
                onClick={onPreprocess}
              >
                {phase3Loading
                  ? "Preprocessing..."
                  : "Preprocess Dataset →"}
              </button>
            </div>
          </div>
        )}

        {preprocessResult && (
          <>
            <div className="success-panel">
              <strong>
                ✓ Preprocessing completed
                successfully
              </strong>

              <span>
                {
                  preprocessResult.missing_values_handled ??
                  0
                }{" "}
                missing value(s) were handled.
              </span>

              <span>
                {
                  preprocessResult.duplicate_records_removed ??
                  0
                }{" "}
                exact duplicate record(s) were
                removed.
              </span>

              <span>
                {preprocessResult.columns_removed
                  ?.length
                  ? preprocessResult.columns_removed
                      .length +
                    " column(s) were removed."
                  : "No columns were removed and extreme values were retained."}
              </span>
            </div>

            <PreprocessingComparison
              before={
                preprocessResult.before || {}
              }
              after={
                preprocessResult.after || {}
              }
            />

            <ActionTable
              columns={selectedColumns}
              actions={
                preprocessResult.actions
              }
              actionText={
                preprocessResult.action_text
              }
            />

            <DatasetPreview
              preview={preview}
              onPage={onPage}
              loading={phase3Loading}
            />

            <div className="next-step">
              <div>
                <p className="eyebrow">
                  NEXT
                </p>

                <h3>
                  3.2 Statistical & Dataset
                  Characteristic Analysis
                </h3>

                <p>
                  Analyze the preprocessed
                  dataset and generate the
                  characteristics used later for
                  model recommendation.
                </p>
              </div>

              <button
                type="button"
                className="primary-button"
                disabled={analysisLoading}
                onClick={onRunAnalysis}
              >
                {analysisLoading
                  ? "Analyzing..."
                  : "Perform Statistical Analysis →"}
              </button>
            </div>
          </>
        )}
      </div>

      {analysis && (
        <StatisticalAnalysis
          result={analysis}
          openSections={openSections}
          onToggle={onToggleAnalysis}
        />
      )}
    </section>
  );
}

/* =========================================================
   PREPROCESSING TABLE
   ========================================================= */

function PreprocessingTable({
  stats,
  onInspect,
}) {
  const columns = stats?.columns || [];

  const missingTotal =
    stats?.missingTotal ??
    stats?.missing_total ??
    0;

  const duplicateValueTotal =
    stats?.duplicateValueTotal ??
    stats?.duplicate_value_total ??
    0;

  const exactDuplicateRows =
    stats?.exactDuplicateRows ??
    stats?.exact_duplicate_rows ??
    0;

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Column</th>
            <th>Data Type</th>
            <th>Missing Values</th>
            <th>Duplicate Values</th>
          </tr>
        </thead>

        <tbody>
          {columns.map((item) => (
            <tr key={item.column}>
              <td>
                <strong>
                  {item.column}
                </strong>
              </td>

              <td>
                {item.dtype || "—"}
              </td>

              <td>
                <CountButton
                  value={item.missing || 0}
                  onClick={() => {
                    if (item.missing > 0) {
                      onInspect({
                        kind: "missing-column",
                        column: item.column,
                        title:
                          "Missing Values · " +
                          item.column,
                      });
                    }
                  }}
                />
              </td>

              <td>
                <CountButton
                  value={
                    item.duplicate_values || 0
                  }
                  onClick={() => {
                    if (
                      item.duplicate_values > 0
                    ) {
                      onInspect({
                        kind:
                          "duplicate-column",
                        column: item.column,
                        title:
                          "Duplicate Values · " +
                          item.column,
                      });
                    }
                  }}
                />
              </td>
            </tr>
          ))}

          <tr className="total-row">
            <td>
              <strong>TOTAL</strong>
            </td>

            <td>—</td>

            <td>
              <CountButton
                value={missingTotal}
                onClick={() => {
                  if (missingTotal > 0) {
                    onInspect({
                      kind: "missing-total",
                      title:
                        "All Missing Values",
                    });
                  }
                }}
              />
            </td>

            <td>
              <CountButton
                value={duplicateValueTotal}
                onClick={() => {
                  if (
                    duplicateValueTotal > 0
                  ) {
                    onInspect({
                      kind:
                        "duplicate-total",
                      title:
                        "All Duplicate Values",
                    });
                  }
                }}
              />
            </td>
          </tr>
        </tbody>
      </table>

      <div className="table-note">
        Exact duplicate records removed
        during preprocessing:{" "}
        <strong>
          {exactDuplicateRows}
        </strong>
      </div>
    </div>
  );
}

/* =========================================================
   COUNT BUTTON
   ========================================================= */

function CountButton({
  value,
  onClick,
}) {
  if (!value) {
    return (
      <span className="zero-count">
        0
      </span>
    );
  }

  return (
    <button
      type="button"
      className="table-count-button"
      onClick={onClick}
    >
      {value}
    </button>
  );
}

/* =========================================================
   INSPECTION MODAL
   ========================================================= */

function InspectionModal({
  payload,
  data,
  loading,
  onClose,
}) {
  const title =
    payload?.title || "Record Inspection";

  return (
    <div className="modal-backdrop">
      <div className="modal-card inspection-modal">
        <button
          type="button"
          className="modal-close"
          onClick={onClose}
        >
          ×
        </button>

        <p className="eyebrow">
          DATA INSPECTION
        </p>

        <h3>{title}</h3>

        {loading ? (
          <div className="inspection-loading">
            Loading affected records…
          </div>
        ) : payload?.kind ===
            "missing-column" &&
          Array.isArray(data) ? (
          <InspectionMissing rows={data} />
        ) : payload?.kind ===
            "duplicate-column" &&
          Array.isArray(data) ? (
          <InspectionDuplicate
            groups={data}
          />
        ) : payload?.kind ===
            "missing-total" &&
          Array.isArray(data) ? (
          <InspectionMissing
            rows={data}
            showColumn
          />
        ) : payload?.kind ===
            "duplicate-total" &&
          Array.isArray(data) ? (
          <InspectionExactDuplicate
            rows={data}
          />
        ) : (
          <div className="empty-state">
            No affected records were found.
          </div>
        )}

        <button
          type="button"
          className="secondary-button"
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  );
}

/* =========================================================
   MISSING INSPECTION
   ========================================================= */

function InspectionMissing({
  rows,
  showColumn = false,
}) {
  return (
    <>
      <p>
        {rows.length} missing value(s)
        found.
      </p>

      <div className="data-table-wrap modal-table">
        <table className="data-table">
          <thead>
            <tr>
              {showColumn && (
                <th>Column</th>
              )}

              <th>Index</th>
              <th>Identifier</th>
              <th>Missing Value</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                {showColumn && (
                  <td>
                    {row.column || "—"}
                  </td>
                )}

                <td>
                  {row.index ??
                    row.__index ??
                    "—"}
                </td>

                <td>
                  {row.identifier ??
                    row.id ??
                    "—"}
                </td>

                <td>
                  {formatMissingValue(row)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* =========================================================
   MISSING VALUE FORMATTER
   ========================================================= */

function formatMissingValue(record) {
  if (
    record?.missing_value !==
      undefined &&
    record?.missing_value !== null
  ) {
    return String(
      record.missing_value
    );
  }

  if (
    record?.value !== undefined &&
    record?.value !== null
  ) {
    return String(record.value);
  }

  if (
    record?.original_value !==
      undefined &&
    record?.original_value !== null
  ) {
    return String(
      record.original_value
    );
  }

  return "Missing";
}

/* =========================================================
   DUPLICATE INSPECTION
   ========================================================= */

function InspectionDuplicate({
  groups,
}) {
  return (
    <>
      <p>
        {groups.length} repeated value
        group(s) found.
      </p>

      <div className="data-table-wrap modal-table">
        <table className="data-table">
          <thead>
            <tr>
              <th>Value</th>
              <th>Index</th>
              <th>Identifier</th>
            </tr>
          </thead>

          <tbody>
            {groups.flatMap(
              (group) =>
                (group.records || []).map(
                  (row, index) => (
                    <tr
                      key={
                        String(
                          group.value
                        ) +
                        "-" +
                        String(
                          row.index ??
                            row.__index ??
                            index
                        ) +
                        "-" +
                        index
                      }
                    >
                      <td>
                        {formatCell(
                          group.value
                        )}
                      </td>

                      <td>
                        {row.index ??
                          row.__index ??
                          "—"}
                      </td>

                      <td>
                        {row.identifier ??
                          row.id ??
                          "—"}
                      </td>
                    </tr>
                  )
                )
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* =========================================================
   EXACT DUPLICATE INSPECTION
   ========================================================= */

function InspectionExactDuplicate({
  rows,
}) {
  return (
    <>
      <p>
        {rows.length} exact duplicate
        record(s) found.
      </p>

      <div className="data-table-wrap modal-table">
        <table className="data-table">
          <thead>
            <tr>
              <th>Index</th>
              <th>Duplicate Of</th>
              <th>Identifier</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td>
                  {row.index ??
                    row.__index ??
                    "—"}
                </td>

                <td>
                  {row.duplicate_of ??
                    "—"}
                </td>

                <td>
                  {row.identifier ??
                    row.id ??
                    "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* =========================================================
   PREPROCESSING COMPARISON
   ========================================================= */

function PreprocessingComparison({
  before,
  after,
}) {
  const rows = [
    [
      "Rows",
      before.rows ?? "—",
      after.rows ?? "—",
    ],
    [
      "Columns",
      before.columns ?? "—",
      after.columns ?? "—",
    ],
    [
      "Missing Values",
      before.missing_values ?? "—",
      after.missing_values ?? "—",
    ],
    [
      "Duplicate Records",
      before.duplicate_records ?? "—",
      after.duplicate_records ?? "—",
    ],
  ];

  return (
    <div className="subsection">
      <h3>
        Preprocessing Summary
      </h3>

      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Before</th>
              <th>After</th>
            </tr>
          </thead>

          <tbody>
            {rows.map(
              ([label, beforeValue, afterValue]) => (
                <tr key={label}>
                  <td>
                    <strong>
                      {label}
                    </strong>
                  </td>

                  <td>{beforeValue}</td>
                  <td>{afterValue}</td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* =========================================================
   ACTION TABLE
   ========================================================= */

function ActionTable({
  columns,
  actions,
  actionText,
}) {
  return (
    <div className="subsection">
      <h3>Actions Applied</h3>

      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>
                Missing-Value Handling
              </th>
              <th>
                Duplicate Handling
              </th>
            </tr>
          </thead>

          <tbody>
            {columns.map((column) => (
              <tr key={column}>
                <td>
                  <strong>
                    {column}
                  </strong>
                </td>

                <td>
                  {actionText?.[column] ||
                    actions?.[column]?.method ||
                    "No missing values"}
                </td>

                <td>
                  Exact duplicate rows only
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* =========================================================
   DATASET PREVIEW
   ========================================================= */

function DatasetPreview({
  preview,
  onPage,
  loading,
}) {
  if (!preview) {
    return null;
  }

  return (
    <div className="subsection">
      <div className="preview-heading">
        <div>
          <h3>
            Preprocessed Dataset
          </h3>

          <p>
            Showing 10 rows at a time •{" "}
            {Number(
              preview.total_rows || 0
            ).toLocaleString()}{" "}
            total rows
          </p>
        </div>

        {loading && (
          <span className="muted">
            Loading…
          </span>
        )}
      </div>

      <div className="data-table-wrap preview-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Index</th>

              {(preview.columns || []).map(
                (column) => (
                  <th key={column}>
                    {column}
                  </th>
                )
              )}
            </tr>
          </thead>

          <tbody>
            {(preview.rows || []).map(
              (row, index) => (
                <tr
                  key={
                    String(
                      row.__index
                    ) +
                    "-" +
                    index
                  }
                >
                  <td>
                    {row.__index}
                  </td>

                  {(preview.columns || []).map(
                    (column) => (
                      <td key={column}>
                        {formatCell(
                          row[column]
                        )}
                      </td>
                    )
                  )}
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={preview.page || 1}
        totalPages={
          preview.total_pages || 1
        }
        onPage={onPage}
      />
    </div>
  );
}

/* =========================================================
   FORMAT CELL
   ========================================================= */

function formatCell(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  return String(value);
}

/* =========================================================
   PAGINATION
   ========================================================= */

function Pagination({
  page,
  totalPages,
  onPage,
}) {
  if (
    !totalPages ||
    totalPages <= 1
  ) {
    return null;
  }

  const pages = [];

  const start = Math.max(
    1,
    page - 2
  );

  const end = Math.min(
    totalPages,
    page + 2
  );

  for (
    let index = start;
    index <= end;
    index += 1
  ) {
    pages.push(index);
  }

  return (
    <div className="pagination">
      <button
        type="button"
        className="secondary-button small"
        disabled={page <= 1}
        onClick={() =>
          onPage(page - 1)
        }
      >
        Previous
      </button>

      {pages.map((number) => (
        <button
          type="button"
          key={number}
          className={
            "page-button" +
            (number === page
              ? " current"
              : "")
          }
          onClick={() =>
            onPage(number)
          }
        >
          {number}
        </button>
      ))}

      <button
        type="button"
        className="secondary-button small"
        disabled={
          page >= totalPages
        }
        onClick={() =>
          onPage(page + 1)
        }
      >
        Next
      </button>
    </div>
  );
}

/* =========================================================
   STATISTICAL ANALYSIS
   ========================================================= */

function StatisticalAnalysis({
  result,
  openSections,
  onToggle,
}) {
  const sections =
    result?.sections || {};

  return (
    <div className="statistical-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            3.2 STATISTICAL & DATASET
            CHARACTERISTIC ANALYSIS
          </p>

          <h3>
            Dataset Characteristics
          </h3>

          <p className="section-subtitle">
            Expand any analysis to see the
            calculated values, the result and
            dynamically generated inference
            points.
          </p>
        </div>
      </div>

      <div className="analysis-overview-card">
        <div>
          <strong>
            Analysis completed
          </strong>

          <span>
            {Number(
              result?.records || 0
            ).toLocaleString()}{" "}
            records ×{" "}
            {result?.features ?? "—"}{" "}
            selected features
          </span>
        </div>

        <div className="analysis-pill">
          Characteristics ready
        </div>
      </div>

      <div className="accordion-list">
        {ANALYSES.map(
          ([key, title]) => {
            const section =
              sections[key];

            if (!section) {
              return null;
            }

            const isOpen =
              Boolean(
                openSections?.[key]
              );

            return (
              <div
                className={
                  "analysis-accordion" +
                  (isOpen
                    ? " open"
                    : "")
                }
                key={key}
              >
                <button
                  type="button"
                  className="analysis-accordion-header"
                  onClick={() =>
                    onToggle(key)
                  }
                >
                  <span className="accordion-arrow">
                    {isOpen
                      ? "⌄"
                      : "›"}
                  </span>

                  <span>
                    {title}
                  </span>

                  <span className="accordion-status">
                    {section.result ||
                      "Completed"}
                  </span>
                </button>

                {isOpen && (
                  <div className="analysis-accordion-body">
                    <AnalysisContent
                      keyName={key}
                      section={section}
                    />
                  </div>
                )}
              </div>
            );
          }
        )}
      </div>

      <div className="success-panel final-analysis">
        <strong>
          ✓ Statistical analysis completed
        </strong>

        <span>
          Dataset characteristics have been
          generated dynamically from the
          preprocessed dataset.
        </span>

        <span>
          These characteristics are ready for
          Phase 4 and Phase 5 model
          recommendation.
        </span>
      </div>
    </div>
  );
}

/* =========================================================
   ANALYSIS CONTENT
   ========================================================= */

function AnalysisContent({
  keyName,
  section,
}) {
  const s = section || {};
  let table = null;

  if (keyName === "overview") {
    const overview =
      s.dataset_overview || {};

    table = (
      <SimpleTable
        rows={[
          ["Records", overview.records],
          ["Features", overview.features],
          [
            "Dataset Size",
            overview.dataset_size,
          ],
          [
            "Dimensionality",
            overview.dimensionality,
          ],
          ["Data Type", overview.data_type],
        ]}
      />
    );
  } else if (keyName === "types") {
    const composition =
      s.feature_composition || {};

    const numerical =
      composition.numerical || {};

    const categorical =
      composition.categorical || {};

    const dateTime =
      composition.date_time || {};

    table = (
      <SimpleTable
        header={[
          "Feature Type",
          "Count",
          "Columns",
        ]}
        rows={[
          [
            "Numerical",
            numerical.count ?? 0,
            (numerical.columns || []).join(
              ", "
            ) || "None",
          ],
          [
            "Categorical",
            categorical.count ?? 0,
            (categorical.columns || []).join(
              ", "
            ) || "None",
          ],
          [
            "Date / Time",
            dateTime.count ?? 0,
            (dateTime.columns || []).join(
              ", "
            ) || "None",
          ],
        ]}
      />
    );
  } else if (
    keyName === "distribution"
  ) {
    table = (
      <ComplexTable
        headers={[
          "Feature",
          "Mean",
          "Median",
          "Std",
          "Skewness",
          "Distribution",
        ]}
        rows={(
          s.distribution_statistics || []
        ).map((row) => [
          row.feature,
          row.mean,
          row.median,
          row.std,
          row.skewness,
          row.distribution,
        ])}
      />
    );
  } else if (keyName === "extreme") {
    table = (
      <ComplexTable
        headers={[
          "Feature",
          "Q1",
          "Q3",
          "Lower Bound",
          "Upper Bound",
          "Extreme Values",
          "%",
        ]}
        rows={(
          s.iqr_analysis || []
        ).map((row) => [
          row.feature,
          row.q1,
          row.q3,
          row.lower_bound,
          row.upper_bound,
          row.extreme_values,
          String(
            row.extreme_percentage ?? 0
          ) + "%",
        ])}
      />
    );
  } else if (keyName === "scale") {
    table = (
      <ComplexTable
        headers={[
          "Feature",
          "Minimum",
          "Maximum",
          "Range",
        ]}
        rows={(
          s.feature_scale || []
        ).map((row) => [
          row.feature,
          row.minimum,
          row.maximum,
          row.range,
        ])}
      />
    );
  } else if (
    keyName === "correlation"
  ) {
    table = (
      <ComplexTable
        headers={[
          "Feature A",
          "Feature B",
          "Correlation",
          "Relationship",
        ]}
        rows={(
          s.pearson_correlation || []
        ).map((row) => [
          row.feature_a,
          row.feature_b,
          row.correlation,
          row.relationship,
        ])}
      />
    );
  } else if (keyName === "cluster") {
    const cluster =
      s.cluster_analysis || {};

    table = (
      <SimpleTable
        rows={[
          [
            "Estimated Clusters",
            cluster.estimated_clusters ??
              "Unavailable",
          ],
          [
            "Silhouette Score",
            cluster.silhouette_score ??
              "Unavailable",
          ],
          [
            "Cluster Structure",
            cluster.cluster_structure ??
              "Unavailable",
          ],
        ]}
      />
    );
  } else if (keyName === "density") {
    const density =
      s.density_analysis || {};

    table = (
      <SimpleTable
        rows={[
          [
            "Mean nearest-neighbor distance",
            density.mean_nearest_neighbor_distance ??
              "Unavailable",
          ],
          [
            "Density variability (CV)",
            density.density_variability_cv ??
              "Unavailable",
          ],
          [
            "Local Density",
            density.local_density ??
              "Unavailable",
          ],
        ]}
      />
    );
  } else if (
    keyName === "temporal"
  ) {
    const temporal =
      s.temporal_structure || {};

    table = (
      <SimpleTable
        rows={[
          [
            "Temporal Column",
            temporal.temporal_column ||
              "Not detected",
          ],
          [
            "Valid Timestamps",
            temporal.valid_timestamps ??
              "Unavailable",
          ],
          [
            "Chronological Ordering",
            temporal.chronological_ordering ??
              "Unavailable",
          ],
          [
            "Interval",
            temporal.interval ??
              "Unavailable",
          ],
          [
            "Regular Intervals",
            temporal.regular_intervals
              ? "Yes"
              : "No",
          ],
        ]}
      />
    );
  } else if (
    keyName === "timeseries"
  ) {
    const pattern =
      s.pattern_analysis || {};

    const sequential =
      pattern.sequential_subsequence ||
      {};

    const periodic =
      pattern.periodic_signal || {};

    const shape =
      pattern.shape_structure || {};

    table = (
      <ComplexTable
        headers={[
          "Pattern",
          "Result",
          "Evidence",
        ]}
        rows={[
          [
            "Sequential / subsequence",
            sequential.result ??
              "Unavailable",
            sequential.evidence ??
              "Unavailable",
          ],
          [
            "Periodic / signal",
            periodic.result ??
              "Unavailable",
            periodic.evidence ??
              "Unavailable",
          ],
          [
            "Shape structure",
            shape.result ??
              "Unavailable",
            shape.evidence ??
              "Unavailable",
          ],
        ]}
      />
    );
  }

  return (
    <>
      <h4>
        {contentTitle(keyName)}
      </h4>

      {table}

      <div className="inference-box">
        <strong>
          What this analysis indicates
        </strong>

        <ul>
          {(s.inferences || [])
            .slice(0, 2)
            .map((text, index) => (
              <li key={index}>
                {text}
              </li>
            ))}
        </ul>
      </div>
    </>
  );
}

/* =========================================================
   CONTENT TITLE
   ========================================================= */

function contentTitle(key) {
  const titles = {
    overview:
      "Dataset Overview",
    types:
      "Feature Composition",
    distribution:
      "Distribution Statistics",
    extreme:
      "IQR Extreme-Value Analysis",
    scale:
      "Feature Range & Scale",
    correlation:
      "Pearson Correlation",
    cluster:
      "K-Means Cluster Structure",
    density:
      "Nearest-Neighbor Density",
    temporal:
      "Temporal Structure",
    timeseries:
      "Time-Series Pattern Analysis",
  };

  return titles[key] || "Analysis";
}

/* =========================================================
   SIMPLE TABLE
   ========================================================= */

function SimpleTable({
  rows,
  header = [
    "Metric",
    "Value",
  ],
}) {
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {header.map((heading) => (
              <th key={heading}>
                {heading}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, valueIndex) => (
                <td key={valueIndex}>
                  {valueIndex === 0 ? (
                    <strong>
                      {String(
                        value ?? "—"
                      )}
                    </strong>
                  ) : (
                    String(
                      value ?? "—"
                    )
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* =========================================================
   COMPLEX TABLE
   ========================================================= */

function ComplexTable({
  headers,
  rows,
}) {
  if (!rows || rows.length === 0) {
    return (
      <div className="empty-state">
        No valid observations were
        available for this analysis.
      </div>
    );
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {headers.map((heading) => (
              <th key={heading}>
                {heading}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, valueIndex) => (
                <td key={valueIndex}>
                  {valueIndex === 0 ? (
                    <strong>
                      {String(
                        value ?? "—"
                      )}
                    </strong>
                  ) : (
                    String(
                      value ?? "—"
                    )
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* =========================================================
   STATUS CARD
   ========================================================= */

function StatusCard({
  text,
  detail,
}) {
  return (
    <div className="status-card">
      <div className="loader" />

      <div>
        <strong>{text}</strong>

        <p>{detail}</p>
      </div>
    </div>
  );
}

/* =========================================================
   CONFIRMATION MODAL
   ========================================================= */

function ConfirmationModal({
  count,
  onProceed,
  onEdit,
}) {
  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <button
          type="button"
          className="modal-close"
          onClick={onEdit}
        >
          ×
        </button>

        <p className="eyebrow">
          SELECTION CONFIRMED
        </p>

        <h3>
          {count} column
          {count === 1 ? "" : "s"} selected
        </h3>

        <p>
          Your current selection is ready.
          Choose whether to continue or edit
          it.
        </p>

        <div className="modal-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={onEdit}
          >
            Edit Column Selection
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={onProceed}
          >
            Proceed to Preprocessing →
          </button>
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   EXPORT
   ========================================================= */

export default App;
