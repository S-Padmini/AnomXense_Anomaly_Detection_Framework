import { useEffect, useMemo, useState } from "react";

import {
  downloadPhase6CSV,
  downloadPhase6Report,
  getPhase6AnomalyDetail,
} from "../../services/phase6Api";

import Investigation, { FilterPanel } from "./Investigation";
import AnomalyDetail from "./AnomalyDetail";

/* =========================================================
   HELPERS
========================================================= */

function number(value, digits = 4) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "—";
}

function percent(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(2)}%` : "—";
}

function status(record) {
  const value = String(record?.status || record?.anomaly_status || "")
    .trim()
    .toLowerCase();
  return value === "anomaly" || value === "outlier" || value.includes("anomal")
    ? "Anomaly"
    : "Normal";
}

function recordSearch(record, columns, query) {
  if (!query) return true;
  const text = query.toLowerCase();
  const values = [
    record?.record_id,
    record?.record_index,
    record?.rank,
    record?.anomaly_score,
    ...columns.map((column) => record?.[column]),
  ];
  return values.some((value) => String(value ?? "").toLowerCase().includes(text));
}

function uniqueColumns(targetColumns = [], explainByColumns = []) {
  return Array.from(new Set([...targetColumns, ...explainByColumns]));
}

function displayModelName(model) {
  if (typeof model === "string") return model;
  if (!model || typeof model !== "object") return "—";
  return (
    model.display_name ||
    model.full_name ||
    model.model_name ||
    model.actual_trained_model ||
    model.selected_model ||
    model.model ||
    model.name ||
    "—"
  );
}

function modelsIncluded(result) {
  if (Array.isArray(result?.trained_models) && result.trained_models.length) {
    return result.trained_models;
  }
  if (Array.isArray(result?.models) && result.models.length) {
    return result.models;
  }
  return [];
}

function modelNamesText(result) {
  const models = modelsIncluded(result);
  if (!models.length) {
    const single = result?.trained_model || result?.selected_model;
    return typeof single === "object" ? displayModelName(single) : single || "—";
  }
  return models.map((model) => displayModelName(model)).join(", ");
}

function actualAnomalyRate(result) {
  const direct = Number(result?.anomaly_rate);
  if (Number.isFinite(direct)) return direct <= 1 ? direct * 100 : direct;
  const total = Number(result?.total_records ?? result?.records_analyzed);
  const anomalies = Number(result?.detected_anomalies);
  if (Number.isFinite(total) && total > 0 && Number.isFinite(anomalies)) {
    return (anomalies / total) * 100;
  }
  return null;
}

function actualContamination(result) {
  const value = Number(result?.contamination);
  if (Number.isFinite(value)) return value <= 1 ? value * 100 : value;
  return actualAnomalyRate(result);
}

function pyodContamination(result) {
  const value = Number(result?.pyod_contamination);
  return Number.isFinite(value) ? (value <= 1 ? value * 100 : value) : null;
}

function approachLabel(result) {
  return result?.approach_label ||
    (result?.approach === "combined_score" ? "Combined Score" : "Best Score");
}

/* =========================================================
   ROADMAP
========================================================= */

function ResultsRoadmap({ active, onChange }) {
  const steps = [
    { id: "summary", number: "01", title: "Summary", text: "Detection overview" },
    { id: "anomalies", number: "02", title: "Detected Anomalies", text: "Investigate records" },
    { id: "visualization", number: "03", title: "Visualization", text: "Explore patterns" },
    { id: "report", number: "04", title: "Report", text: "Download results" },
  ];

  
  return (
    <div className="p6-roadmap">
      {steps.map((step, index) => (
        <div className={`p6-roadmap-step${active === step.id ? " active" : ""}`} key={step.id}>
          <button type="button" onClick={() => onChange(step.id)}>
            <span className="p6-roadmap-number">{step.number}</span>
            <span className="p6-roadmap-copy">
              <strong>{step.title}</strong>
              <small>{step.text}</small>
            </span>
          </button>
          {index < steps.length - 1 && <span className="p6-roadmap-line" />}
        </div>
      ))}
    </div>
  );
}

/* =========================================================
   SUMMARY
========================================================= */

function SummaryView({ result, onBack }) {
  const totalRecords = Number(result?.total_records ?? result?.records_analyzed);
  const anomalies = Number(result?.detected_anomalies);
  const normalRecords = Number(
    result?.normal_records ??
      (Number.isFinite(totalRecords) && Number.isFinite(anomalies)
        ? totalRecords - anomalies
        : NaN)
  );
  const anomalyRate = actualAnomalyRate(result);
  const models = modelsIncluded(result);
  const modelText = modelNamesText(result);
  const targetText = Array.isArray(result?.target_columns) && result.target_columns.length
    ? result.target_columns.join(", ")
    : "—";
  const explainText = Array.isArray(result?.explain_by_columns) && result.explain_by_columns.length
    ? result.explain_by_columns.join(", ")
    : "—";
  const objectiveText =
    result?.journey?.phase4_objective_understanding?.interpreted_objective ||
    result?.journey?.phase4_objective_understanding?.objective_understanding ||
    result?.journey?.phase4_objective_understanding?.explanation ||
    result?.objective ||
    "Objective information is not available.";
  const threshold = number(result?.threshold, 6);
  const contamination = pyodContamination(result);

  return (
    <>
      <style>{`
        /* Detection Overview table: subtle readability increase */
        .p6-summary-view .p6-detection-overview-table th,
        .p6-summary-view .p6-detection-overview-table td {
        font-size: 90% !important;
}
      `}</style>
      <div className="p6-result-view p6-summary-view">
      <div className="p6-result-heading">
        <div>
          <span className="p6-section-kicker">01 · SUMMARY</span>
          <h3>Detection Overview</h3>
          <p>A factual summary of the completed Phase 6 detection run.</p>
        </div>

        <button
          type="button"
          className="p6-secondary-button"
          onClick={onBack}
        >
          ← Back
        </button>
      </div>

      <section className="p6-overview-card">
        <div className="p6-overview-card-head">
          <div>
            <span className="p6-section-kicker">ACTUAL BACKEND RESULT</span>
            <h4>Detection Overview</h4>
          </div>
          <span className="p6-backend-badge">Phase 6 Backend</span>
        </div>

        <div className="p6-overview-table-wrap">
          <table className="p6-detection-overview-table">
            <tbody>
              <SummaryRowTable label="Total Records Processed" value={Number.isFinite(totalRecords) ? totalRecords : "—"} />
              <SummaryRowTable label="Anomaly Records Count" value={Number.isFinite(anomalies) ? anomalies : "—"} />
              <SummaryRowTable label="Normal Record Count" value={Number.isFinite(normalRecords) ? normalRecords : "—"} />
              <SummaryRowTable label="Anomaly Rate" value={percent(anomalyRate)} />
              <SummaryRowTable label="Approach Used" value={approachLabel(result)} />
              <SummaryRowTable label="Models Used" value={modelText} />
              <SummaryRowTable
                label="Threshold / Contamination"
                value={`Threshold: ${threshold} | PyOD contamination: ${contamination == null ? "—" : percent(contamination)}`}
              />
              <SummaryRowTable label="Target" value={targetText} />
              <SummaryRowTable label="Explain By" value={explainText} />
              <SummaryRowTable label="Objective" value={objectiveText} long />
            </tbody>
          </table>
        </div>

        <p className="p6-backend-note">
          Threshold and contamination values shown above are taken from the fitted backend PyOD detection result.
          The frontend does not calculate or override the classification threshold.
        </p>
      </section>

      {models.length > 0 && (
        <div className="p6-model-runtime-strip" aria-label="Models used">
          {models.map((model, index) => (
            <span className="p6-model-chip" key={`${displayModelName(model)}-${index}`}>
              {displayModelName(model)}
            </span>
          ))}
        </div>
      )}
    </div>
    </>
  );
}

function SummaryRowTable({ label, value, long = false }) {
  return (
    <tr className={long ? "p6-overview-objective-row" : ""}>
      <th scope="row">{label}</th>
      <td>{value ?? "—"}</td>
    </tr>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="p6-summary-row">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

/* =========================================================
   VISUALIZATION
========================================================= */

function inferLocalChartType(records, column) {
  const values = records
    .map((record) => record?.[column])
    .filter((value) => value !== null && value !== undefined && value !== "");

  if (!values.length) return "score_vs_feature";

  const numericCount = values.reduce((count, value) => {
    return count + (Number.isFinite(Number(value)) ? 1 : 0);
  }, 0);

  if (numericCount >= Math.max(3, Math.ceil(values.length * 0.7))) {
    return "score_vs_feature";
  }

  const unique = new Set(values.map((value) => String(value)));
  return unique.size <= 50 ? "categorical_anomaly_rate" : "score_vs_feature";
}

function VisualizationView({ result, records, search, onSearch, onSelect, schema, filters, onFiltersChange, onResetFilters }) {
  const targetColumns = Array.isArray(result?.target_columns) ? result.target_columns : [];
  const explainByColumns = Array.isArray(result?.explain_by_columns) ? result.explain_by_columns : [];
  const columns = useMemo(() => uniqueColumns(targetColumns, explainByColumns), [targetColumns, explainByColumns]);
  const [zoomByTarget, setZoomByTarget] = useState({});

  const filteredRecords = useMemo(() => {
    const query = search.trim().toLowerCase();
    return records
      .filter((record) => recordSearch(record, columns, query))
      .filter((record) => Object.entries(filters || {}).every(([column, filter]) => {
        if (!filter || filter === "") return true;
        const value = record?.[column];
        if (Array.isArray(filter)) return !filter.length || filter.includes(String(value));
        if (typeof filter === "object" && filter !== null) {
          if (filter.min !== undefined && filter.min !== "") {
            const numeric = Number(value);
            if (!Number.isFinite(numeric) || numeric < Number(filter.min)) return false;
          }
          if (filter.max !== undefined && filter.max !== "") {
            const numeric = Number(value);
            if (!Number.isFinite(numeric) || numeric > Number(filter.max)) return false;
          }
          if (filter.from && String(value) < filter.from) return false;
          if (filter.to && String(value) > filter.to) return false;
          return true;
        }
        return String(value ?? "").toLowerCase().includes(String(filter).toLowerCase());
      }));
  }, [records, columns, search, filters]);

  function changeZoom(column, delta) {
    setZoomByTarget((current) => {
      const currentZoom = Number(current[column] || 1);
      const next = Math.max(0.6, Math.min(2.5, currentZoom + delta));
      return { ...current, [column]: Number(next.toFixed(1)) };
    });
  }

  function resetZoom(column) {
    setZoomByTarget((current) => ({ ...current, [column]: 1 }));
  }

  return (
    <div className="p6-result-view">
      <div className="p6-result-heading">
        <div>
          <span className="p6-section-kicker">03 · VISUALIZATION</span>
          <h3>Explore Detection Patterns</h3>
          <p>All analyzed records are shown. Normal and anomaly records remain directly connected to the investigation explanation.</p>
        </div>
      </div>

      <div className="p6-visual-filter-shell">
        <FilterPanel
          schema={schema}
          records={records}
          filters={filters}
          onChange={onFiltersChange}
          onReset={onResetFilters}
        />
      </div>

      <div className="p6-visual-search">
        <div className="p6-search-box large">
          <span>⌕</span>
          <input
            type="text"
            placeholder="Search record or selected feature..."
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
        </div>
      </div>

      <div className="p6-visual-scope-grid">
        <div className="p6-visual-scope">
          <span>Target columns</span>
          <div>{targetColumns.length ? targetColumns.map((column) => <span className="p6-scope-chip active" key={column}>{column}</span>) : <span className="p6-muted">No target columns</span>}</div>
        </div>
        <div className="p6-visual-scope">
          <span>Explain By columns</span>
          <div>{explainByColumns.length ? explainByColumns.map((column) => <span className="p6-scope-chip" key={column}>{column}</span>) : <span className="p6-muted">None selected</span>}</div>
        </div>
      </div>

      <div className="p6-visual-legend">
        <span><i className="p6-legend-dot normal" />Normal</span>
        <span><i className="p6-legend-dot anomaly" />Anomaly</span>
        <span>{filteredRecords.length} records shown</span>
      </div>

      {!targetColumns.length && (
        <div className="p6-empty-card">No Target columns were selected for visualization.</div>
      )}

      {targetColumns.map((targetColumn, index) => {
        const chartType = inferLocalChartType(filteredRecords, targetColumn);
        const zoom = Number(zoomByTarget[targetColumn] || 1);
        return (
          <section className="p6-chart-card p6-multi-target-chart" key={targetColumn}>
            <div className="p6-chart-header">
              <div>
                <span className="p6-section-kicker">TARGET {String(index + 1).padStart(2, "0")}</span>
                <h4>{targetColumn}</h4>
                <p>{chartType === "categorical_anomaly_rate" ? `Anomaly distribution across ${targetColumn}.` : `Displaying all analyzed records against ${targetColumn}; backend anomaly status controls the point classification.`}</p>
              </div>
              <div className="p6-chart-toolbar" aria-label={`Zoom controls for ${targetColumn}`}>
                <button type="button" onClick={() => changeZoom(targetColumn, -0.2)} aria-label={`Zoom out ${targetColumn}`}>−</button>
                <span>{Math.round(zoom * 100)}%</span>
                <button type="button" onClick={() => changeZoom(targetColumn, 0.2)} aria-label={`Zoom in ${targetColumn}`}>+</button>
                <button type="button" onClick={() => resetZoom(targetColumn)}>Reset</button>
              </div>
            </div>
            <div className="p6-chart-zoom-viewport">
              <div className="p6-chart-zoom-content" style={{ transform: `scale(${zoom})` }}>
                <DynamicChart records={filteredRecords} xColumn={targetColumn} chartType={chartType} onSelect={onSelect} />
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}

/* =========================================================
   DYNAMIC SVG / BAR CHART
========================================================= */

function DynamicChart({ records, xColumn, chartType, onSelect }) {
  if (!records.length) return <div className="p6-chart-empty">No data available for the current visualization filters.</div>;

  if (chartType === "categorical_anomaly_rate") {
    const groups = {};
    records.forEach((record) => {
      const key = String(record?.[xColumn] ?? "Unknown");
      if (!groups[key]) groups[key] = { total: 0, anomalies: 0, records: [] };
      groups[key].total += 1;
      groups[key].records.push(record);
      if (status(record) === "Anomaly") groups[key].anomalies += 1;
    });
    const entries = Object.entries(groups)
      .map(([category, data]) => ({ category, ...data, rate: data.total ? (data.anomalies / data.total) * 100 : 0 }))
      .sort((a, b) => b.rate - a.rate)
      .slice(0, 12);

    return (
      <div className="p6-bar-chart">
        {entries.map((entry) => (
          <div className="p6-bar-group" key={entry.category}>
            <div className="p6-bar-value">{entry.rate.toFixed(1)}%</div>
            <button
              type="button"
              className="p6-bar"
              style={{ height: `${Math.max(8, Math.min(100, entry.rate))}%` }}
              title={`${entry.anomalies} anomalies out of ${entry.total} records. Click to inspect a record.`}
              onClick={() => {
                const selected = entry.records.find((record) => status(record) === "Anomaly") || entry.records[0];
                if (selected) onSelect(selected);
              }}
            />
            <span>{entry.category}</span>
            <small>{entry.anomalies}/{entry.total} anomalies</small>
          </div>
        ))}
      </div>
    );
  }

  const numericPoints = records.map((record) => {
    const x = Number(record?.[xColumn]);
    const y = Number(record?.anomaly_score);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return { record, x, y, status: status(record) };
  }).filter(Boolean);

  if (!numericPoints.length) {
    return <div className="p6-chart-empty">The selected Target does not contain enough numeric values for a score visualization.</div>;
  }

  const width = 900, height = 360, padding = 50;
  const xs = numericPoints.map((point) => point.x);
  const ys = numericPoints.map((point) => point.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);

  return (
    <div className="p6-svg-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} className="p6-svg-chart" role="img" aria-label={`${xColumn} anomaly visualization`}>
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="p6-chart-axis" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="p6-chart-axis" />
        {numericPoints.map((point, index) => {
          const x = padding + ((point.x - minX) / (maxX - minX || 1)) * (width - padding * 2);
          const y = height - padding - ((point.y - minY) / (maxY - minY || 1)) * (height - padding * 2);
          const isAnomaly = point.status === "Anomaly";
          return (
            <circle
              key={`${point.record?.record_index}-${index}`}
              cx={x}
              cy={y}
              r={isAnomaly ? 6 : 4}
              className={isAnomaly ? "p6-chart-dot anomaly" : "p6-chart-dot normal"}
              onClick={() => onSelect(point.record)}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(point.record);
                }
              }}
            >
              <title>{isAnomaly ? `ANOMALY · ${String(point.record?.record_id ?? point.record?.record_index ?? "—")} · score ${number(point.record?.anomaly_score, 6)}` : `NORMAL · ${String(point.record?.record_id ?? point.record?.record_index ?? "—")} · score ${number(point.record?.anomaly_score, 6)}`}</title>
            </circle>
          );
        })}
      </svg>
      <div className="p6-chart-axis-labels"><span>{xColumn}</span><span>Anomaly Score</span></div>
    </div>
  );
}

/* =========================================================
   REPORT
========================================================= */

function ReportView({ datasetId, result, objective }) {
  const [downloading, setDownloading] = useState(false);
  const [csvDownloading, setCsvDownloading] = useState(false);
  const [error, setError] = useState("");

  async function downloadPDF() {
    setDownloading(true); setError("");
    try { await downloadPhase6Report(datasetId); }
    catch (err) { setError(err?.message || "Unable to download report."); }
    finally { setDownloading(false); }
  }

  async function downloadCSV() {
    setCsvDownloading(true); setError("");
    try { await downloadPhase6CSV(datasetId); }
    catch (err) { setError(err?.message || "Unable to download anomaly CSV."); }
    finally { setCsvDownloading(false); }
  }

  const journey = result?.journey || {};
  const allRecords = Array.isArray(result?.records) ? result.records : [];
  const anomalies = allRecords.filter((record) => status(record) === "Anomaly");
  const models = modelsIncluded(result);
  const reportColumns = uniqueColumns(result?.target_columns || [], result?.explain_by_columns || []);
  const totalRecords = Number(result?.total_records ?? result?.records_analyzed);
  const anomalyCount = Number(result?.detected_anomalies);
  const anomalyRate = actualAnomalyRate(result);

  return (
    <div className="p6-result-view">
      <div className="p6-result-heading">
        <div>
          <span className="p6-section-kicker">04 · REPORT</span>
          <h3>Detection Report</h3>
          <p>The downloadable report uses the actual completed Phase 1–6 session.</p>
        </div>
        <div className="p6-report-actions">
          <button type="button" className="p6-secondary-button" onClick={downloadCSV} disabled={csvDownloading}>{csvDownloading ? "Preparing CSV..." : "Download Anomaly CSV"}</button>
          <button type="button" className="p6-train-button small" onClick={downloadPDF} disabled={downloading}>{downloading ? "Preparing PDF..." : "Download Full PDF"}</button>
        </div>
      </div>

      {error && <div className="p6-error-card">{error}</div>}

      <div className="p6-report-preview">
        <div className="p6-report-cover"><span>INTELLIGENT ANOMALY INSIGHTS</span><h3>Anomaly Detection Report</h3><p>Complete Phase 1 → Phase 6 analytical journey.</p></div>

        <ReportSection title="Framework">
          <ul className="p6-report-points">
            <li>Intelligent anomaly detection combines dataset understanding, statistical analysis, objective understanding and model-based detection.</li>
            <li>Phase 6 uses the selected detection features and actual model output as the source of anomaly results.</li>
          </ul>
        </ReportSection>

        <ReportSection title="Dataset Overview"><pre>{JSON.stringify(journey?.phase1_dataset_overview || {}, null, 2)}</pre></ReportSection>

        <ReportSection title="Phase 2 — Column Selection">
          <p>Columns available for investigation:</p>
          <ChipGroup values={journey?.phase2_selected_columns || []} />
          <div className="p6-report-role-grid">
            <div><strong>Target columns</strong><ChipGroup values={result?.target_columns || []} /></div>
            <div><strong>Explain By columns</strong><ChipGroup values={result?.explain_by_columns || []} /></div>
          </div>
        </ReportSection>

        <ReportSection title="Phase 3 — Preprocessing"><pre>{JSON.stringify(journey?.phase3_preprocessing || journey?.phase3_preprocessing_summary || {}, null, 2)}</pre></ReportSection>
        <ReportSection title="Phase 3 — Statistical Analysis"><pre>{JSON.stringify(journey?.phase3_statistical_analysis || {}, null, 2)}</pre></ReportSection>

        <ReportSection title="Phase 4 — Objective Understanding">
          <p>{objective || journey?.phase4_objective_understanding?.interpreted_objective || journey?.phase4_objective_understanding?.objective_understanding || "Objective information is not available."}</p>
          {journey?.phase4_objective_understanding && <pre>{JSON.stringify(journey.phase4_objective_understanding, null, 2)}</pre>}
        </ReportSection>

        <ReportSection title="Phase 5 — Recommended Models">
          <div className="p6-report-models">
            {models.length ? models.map((model, index) => (
              <div key={model?.model || model?.display_name || index}>
                <strong>{displayModelName(model)}</strong>
                {model?.weight !== undefined && <span>Weight {number(model.weight, 4)}</span>}
                {model?.final_score !== undefined && <span>Phase 5 score {number(model.final_score, 4)}</span>}
              </div>
            )) : <div className="p6-muted">No model recommendation data was returned.</div>}
          </div>
        </ReportSection>

        <ReportSection title="Phase 6 — Approach Selected">
          <div className="p6-report-summary-grid">
            <SummaryRow label="Approach" value={approachLabel(result)} />
            <SummaryRow label="Models included" value={modelNamesText(result)} />
            <SummaryRow label="Target columns" value={result?.target_columns?.join(", ") || "—"} />
            <SummaryRow label="Explain By columns" value={result?.explain_by_columns?.join(", ") || "—"} />
            <SummaryRow label="Threshold" value={number(result?.threshold, 6)} />
            <SummaryRow label="Observed contamination / anomaly rate" value={percent(actualContamination(result))} />
            <SummaryRow label="PyOD contamination" value={percent(pyodContamination(result))} />
          </div>
        </ReportSection>

        <ReportSection title="Phase 6 — Model Training & Anomaly Summary">
          <div className="p6-report-summary-grid">
            <SummaryRow label="Records analyzed" value={Number.isFinite(totalRecords) ? totalRecords : "—"} />
            <SummaryRow label="Detected anomalies" value={Number.isFinite(anomalyCount) ? anomalyCount : "—"} />
            <SummaryRow label="Normal records" value={result?.normal_records ?? "—"} />
            <SummaryRow label="Anomaly rate" value={percent(anomalyRate)} />
            <SummaryRow label="Approach used" value={approachLabel(result)} />
            <SummaryRow label="Models included" value={modelNamesText(result)} />
            <SummaryRow label="Threshold" value={number(result?.threshold, 6)} />
            <SummaryRow label="PyOD contamination" value={percent(pyodContamination(result))} />
          </div>
          <div className="p6-report-note">Anomaly status shown in this report is taken directly from the completed backend detection result.</div>
        </ReportSection>

        <ReportSection title={`Detected Anomaly Records (${anomalies.length})`}>
          <div className="p6-table-container">
            <table className="p6-investigation-table">
              <thead><tr><th>Rank</th><th>Record</th><th>Status</th><th>Score</th>{reportColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
              <tbody>
                {anomalies.slice(0, 200).map((record, index) => (
                  <tr key={`${record?.record_index}-${index}`}>
                    <td>{record?.rank ?? index + 1}</td>
                    <td>{String(record?.record_id ?? record?.record_index ?? "—")}</td>
                    <td><span className="p6-status-badge anomaly">Anomaly</span></td>
                    <td>{number(record?.anomaly_score, 6)}</td>
                    {reportColumns.map((column) => <td key={column}>{String(record?.[column] ?? "—")}</td>)}
                  </tr>
                ))}
                {!anomalies.length && <tr><td colSpan={reportColumns.length + 4} className="p6-empty-table">No anomalies were detected in the completed run.</td></tr>}
              </tbody>
            </table>
          </div>
        </ReportSection>

        <ReportSection title="Overall Target Column Visualization">
          <p>The interactive visualization uses the actual Phase 6 records. Normal records remain normal, while only backend-classified anomalies are highlighted.</p>
          <div className="p6-report-role-grid">
            <div><strong>Target columns</strong><ChipGroup values={result?.target_columns || []} /></div>
            <div><strong>Explain By columns</strong><ChipGroup values={result?.explain_by_columns || []} /></div>
          </div>
        </ReportSection>

        <ReportSection title="Conclusion">
          <p>The completed Phase 6 run analyzed {result?.records_analyzed ?? "the available"} records and classified {result?.detected_anomalies ?? "the detected"} records as anomalies using the {approachLabel(result)} approach.</p>
          <p>The anomaly findings are based on the actual model score and backend detection threshold. Target columns provide the model detection evidence, while Explain By columns provide the investigator-selected contextual perspective.</p>
          <p>Feature-level explanations should be interpreted as model/data evidence and not as proof of causal root cause.</p>
        </ReportSection>
      </div>
    </div>
  );
}

function ReportSection({ title, children }) {
  return <section className="p6-report-section"><h4>{title}</h4>{children}</section>;
}

function ChipGroup({ values = [] }) {
  return <div className="p6-report-chips">{values.length ? values.map((value) => <span key={value}>{value}</span>) : <span className="p6-muted">None</span>}</div>;
}

/* =========================================================
   MAIN RESULTS COMPONENT
========================================================= */

export default function DetectionResults({
  datasetId,
  result,
  objective,
  onBack,
}) {
  const [view, setView] = useState("summary");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({});
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const allRecords = Array.isArray(result?.records) ? result.records : [];
  const investigationColumns = useMemo(() => uniqueColumns(result?.target_columns || [], result?.explain_by_columns || []), [result?.target_columns, result?.explain_by_columns]);
  const backendSchema = Array.isArray(result?.filter_schema)
    ? result.filter_schema
    : [];

  // Always expose every selected Target + Explain By column.
  // The backend schema is preferred; missing columns are inferred from the
  // actual records so a newly selected context column never disappears.
  const schema = useMemo(() => {
    const byColumn = new Map(backendSchema.map((item) => [item?.column, item]));
    return investigationColumns.map((column) => {
      if (byColumn.has(column)) return byColumn.get(column);
      const values = allRecords.map((record) => record?.[column]).filter((value) => value !== null && value !== undefined && value !== "");
      const numeric = values.length > 0 && values.every((value) => Number.isFinite(Number(value)));
      const unique = [...new Set(values.map((value) => String(value)))];
      return {
        column,
        type: numeric ? "numeric" : unique.length <= 50 ? "categorical" : "text",
        values: numeric ? undefined : unique,
        min: numeric && values.length ? Math.min(...values.map(Number)) : undefined,
        max: numeric && values.length ? Math.max(...values.map(Number)) : undefined,
      };
    });
  }, [backendSchema, investigationColumns, allRecords]);

  const filteredRecords = useMemo(() => {
    const query = search.trim().toLowerCase();
    return allRecords
      .filter((record) => status(record) === "Anomaly")
      .filter((record) => recordSearch(record, investigationColumns, query))
      .filter((record) => Object.entries(filters).every(([column, filter]) => {
        if (!filter || filter === "") return true;
        const value = record?.[column];
        if (Array.isArray(filter)) return !filter.length || filter.includes(String(value));
        if (typeof filter === "object" && filter !== null) {
          if (filter.min !== undefined && filter.min !== "") {
            const numeric = Number(value);
            if (!Number.isFinite(numeric) || numeric < Number(filter.min)) return false;
          }
          if (filter.max !== undefined && filter.max !== "") {
            const numeric = Number(value);
            if (!Number.isFinite(numeric) || numeric > Number(filter.max)) return false;
          }
          if (filter.from && String(value) < filter.from) return false;
          if (filter.to && String(value) > filter.to) return false;
          return true;
        }
        return String(value ?? "").toLowerCase().includes(String(filter).toLowerCase());
      }));
  }, [allRecords, search, filters, investigationColumns]);

  function resetFilters() {
    setFilters({});
    setSearch("");
  }

  async function handleSelectRecord(record) {
    if (!record) return;

    setDetailError("");
    setDetailLoading(true);

    // Open immediately with the record already available. The backend detail
    // endpoint is then used to enrich it with the authoritative explanation.
    setSelectedRecord(record);

    try {
      const recordIndex = record?.record_index ?? record?.original_row_index ?? record?.id;
      if (recordIndex === undefined || recordIndex === null || recordIndex === "") {
        return;
      }

      const response = await getPhase6AnomalyDetail(datasetId, recordIndex);
      const detail = response?.detail || response?.result || response;
      const detailRecord = detail?.record || detail?.anomaly || detail?.data || {};
      const detailExplanation = detail?.explanation || detailRecord?.explanation || {};

      setSelectedRecord({
        ...record,
        ...detailRecord,
        explanation: {
          ...(record?.explanation || {}),
          ...(detailExplanation || {}),
        },
      });
    } catch (error) {
      // Keep the clicked record visible even if the optional detail request fails.
      // This prevents a backend detail failure from blanking the Phase 6 screen.
      console.error("PHASE 6 ANOMALY DETAIL ERROR:", error);
      setDetailError(error?.message || "Unable to load anomaly explanation.");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="p6-results">
      <div className="p6-results-hero">
        <div>
          <span className="p6-section-kicker">PHASE 06 · DETECTION COMPLETE</span>
          <h2>Anomaly Detection Results</h2>
          <p>The completed detection run is ready for summary, investigation, visualization and reporting.</p>
        </div>
        <div className="p6-complete-badge"><span>✓</span>Detection completed</div>
      </div>

      <ResultsRoadmap active={view} onChange={setView} />

      {view === "summary" && (
        <SummaryView
          result={result}
          onBack={onBack}
        />
      )}

      {view === "anomalies" && (
        <div className="p6-result-view">
          <FilterPanel schema={schema} records={allRecords} filters={filters} onChange={setFilters} onReset={resetFilters} />
          <Investigation records={filteredRecords} result={result} search={search} onSearch={setSearch} onSelect={handleSelectRecord} />
        </div>
      )}

      {view === "visualization" && (
        <VisualizationView
          datasetId={datasetId}
          result={result}
          records={allRecords}
          search={search}
          onSearch={setSearch}
          onSelect={handleSelectRecord}
          schema={schema}
          filters={filters}
          onFiltersChange={setFilters}
          onResetFilters={resetFilters}
        />
      )}

      {view === "report" && <ReportView datasetId={datasetId} result={result} objective={objective} />}

      {detailLoading && selectedRecord && (
        <div className="p6-detail-loading" role="status">Loading anomaly explanation…</div>
      )}

      {detailError && selectedRecord && (
        <div className="p6-detail-error" role="alert">{detailError}</div>
      )}

      {selectedRecord && (
        <AnomalyDetail record={selectedRecord} result={result} objective={objective} onClose={() => setSelectedRecord(null)} />
      )}
    </div>
  );
}
