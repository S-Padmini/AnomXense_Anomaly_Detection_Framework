import React from "react";

function formatScore(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(6) : "—";
}

function formatPercent(value, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(digits)}%` : "—";
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : "—";
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") {
    try { return JSON.stringify(value); } catch { return String(value); }
  }
  return String(value);
}

function humanize(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

function getStatus(record) {
  const raw = record?.status ?? record?.anomaly_status;
  if (raw !== null && raw !== undefined && String(raw).trim()) {
    const value = String(raw).trim().toLowerCase();
    if (value === "anomaly" || value === "outlier" || value.includes("anomal")) return "Anomaly";
    if (value === "normal" || value === "inlier") return "Normal";
  }
  if (typeof record?.is_anomaly === "boolean") return record.is_anomaly ? "Anomaly" : "Normal";
  if (typeof record?.prediction === "number") return record.prediction === 1 ? "Anomaly" : "Normal";
  return "Unknown";
}

function getIdentifier(record) {
  return String(
    record?.record_id ??
    record?.customer_id ??
    record?.id ??
    record?.record_index ??
    "—"
  );
}

function getModelName(result, record, explanation) {
  const candidates = [
    explanation?.model_name,
    explanation?.model,
    record?.actual_model,
    record?.trained_model,
    record?.selected_model,
    record?.model_name,
    record?.model,
    result?.actual_model,
    result?.trained_model,
    result?.selected_model,
    result?.model_name,
    result?.model,
  ];
  for (const value of candidates) {
    if (typeof value === "string" && value.trim()) return value;
    if (value && typeof value === "object") {
      const nested = value.display_name || value.full_name || value.model_name || value.actual_trained_model || value.selected_model || value.model || value.name;
      if (nested) return String(nested);
    }
  }
  return result?.approach === "combined_score" || result?.approach_label === "Combined Score"
    ? "Combined Score"
    : "—";
}

function getShapEvidence(explanation) {
  const evidence = Array.isArray(explanation?.target_feature_evidence)
    ? explanation.target_feature_evidence
    : [];

  return evidence
    .filter((item) => String(item?.method || "").trim().toLowerCase() === "shap")
    .map((item) => ({
      ...item,
      contributionPercent: Number(
        item?.shap_contribution_percent ?? item?.contribution_percent
      ),
      absoluteShap: Math.abs(
        Number(item?.shap_abs_value ?? item?.contribution ?? item?.signed_contribution ?? 0)
      ),
    }))
    .filter((item) => Number.isFinite(item.contributionPercent) && Number.isFinite(item.absoluteShap))
    .sort((a, b) => b.absoluteShap - a.absoluteShap);
}

function getExplainByContext(record, explanation) {
  const context = Array.isArray(explanation?.explain_by_context)
    ? explanation.explain_by_context
    : [];

  if (context.length) {
    return context
      .filter(
        (item) =>
          item?.column &&
          item?.value !== undefined &&
          item?.value !== null &&
          String(item.value).trim() !== ""
      )
      .map((item) => ({
        column: item.column,
        label: item.label || humanize(item.column),
        value: item.value,
      }));
  }

  // Fallback only when the backend provides the selected Explain By
  // column names but not explain_by_context.
  const selectedColumns = Array.isArray(explanation?.explain_by_columns)
    ? explanation.explain_by_columns
    : [];

  return selectedColumns
    .filter(
      (column) =>
        record?.[column] !== undefined &&
        record?.[column] !== null &&
        String(record[column]).trim() !== ""
    )
    .map((column) => ({
      column,
      label: humanize(column),
      value: record[column],
    }));
}

function getShapDirection(item) {
  const signed = Number(item?.shap_value ?? item?.signed_contribution);

  if (Number.isFinite(signed)) {
    if (signed > 0) return "increasing";
    if (signed < 0) return "decreasing";
  }

  const direction = String(item?.direction || "").toLowerCase();

  if (direction.includes("increase")) return "increasing";
  if (direction.includes("decrease")) return "decreasing";

  return "influencing";
}

function ShapFeatureContribution({ record, explanation, identifier, score, threshold, isAnomaly }) {
  const evidence = getShapEvidence(explanation);
  const topFeatures = evidence.slice(0, 3);
  const topFeature = topFeatures[0];
  const explainBy = getExplainByContext(record, explanation);

  const explainByText = explainBy.length
    ? explainBy
        .map((item) => `${humanize(item.label || item.column)} ${displayValue(item.value)}`)
        .join(", ")
    : "";

  const statusText = isAnomaly ? "is identified as an anomaly" : "is identified as normal";
  const comparisonText =
    Number.isFinite(score) && Number.isFinite(threshold)
      ? score > threshold
        ? `is above the detection threshold of ${formatScore(threshold)}`
        : score < threshold
          ? `is below the detection threshold of ${formatScore(threshold)}`
          : `is equal to the detection threshold of ${formatScore(threshold)}`
      : "cannot be compared with the detection threshold because the required values are unavailable";

  return (
    <>
      <section className="p6-detail-section p6-shap-contribution-section">
        <div className="p6-detail-section-head">
          <div className="p6-detail-section-icon">◈</div>
          <div>
            <h3>FEATURE CONTRIBUTION</h3>
            <p>Top contributing features according to SHAP.</p>
          </div>
        </div>

        {topFeatures.length > 0 ? (
          <div className="p6-shap-feature-list">
            {topFeatures.map((item, index) => {
              const percent = Math.max(0, Math.min(100, item.contributionPercent));
              const name = humanize(item?.label || item?.column || item?.feature || "Feature");

              return (
                <div
                  className="p6-shap-feature-row"
                  key={`${item?.column || item?.feature || "feature"}-${index}`}
                >
                  <div className="p6-shap-feature-main">
                    <div className="p6-shap-feature-line">
                      <span className="p6-shap-feature-name">{name}</span>
                      <strong>{formatPercent(percent)}</strong>
                    </div>
                    <div className="p6-shap-feature-track">
                      <span
                        className="p6-shap-feature-fill"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p6-shap-empty">
            SHAP feature contribution was not returned by the backend for this record.
          </div>
        )}
      </section>

      <section className="p6-detail-section p6-shap-how-section">
        <div className="p6-detail-section-head">
          <div className="p6-detail-section-icon">◉</div>
          <div>
            <h3>HOW SHAP EXPLAINS THIS ANOMALY</h3>
          </div>
        </div>

        <div className="p6-shap-how-card">
          <p>
            <strong>Method: Local SHAP (SHapley Additive exPlanations)</strong>
          </p>

          <p>
            SHAP explains the influence of each feature on the anomaly score for
            this specific record. Larger absolute SHAP values indicate greater
            influence.
          </p>

          <div className="p6-shap-calculation">
            <span>CALCULATION</span>
            <strong>
              Contribution % = |Feature SHAP value| ÷ Σ|All SHAP values| × 100
            </strong>
          </div>

          {explainBy.length > 0 && (
            <div className="p6-shap-context">
              <h4>EXPLAIN BY — RECORD CONTEXT</h4>

              <div className="p6-context-grid">
                {explainBy.map((item) => (
                  <div className="p6-context-card" key={item.column}>
                    <span>{humanize(item.label || item.column)}</span>
                    <strong>{displayValue(item.value)}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="p6-shap-summary">
            <h4>SUMMARY</h4>

            <ol className="p6-reason-list">
              <li>
                Record {identifier}
                {explainByText ? `, ${explainByText},` : ""}
                {" "}
                {statusText} because its anomaly score of{" "}
                {formatScore(score)} {comparisonText}.
              </li>

              {topFeature ? (
                <li>
                  {humanize(
                    topFeature?.label ||
                    topFeature?.column ||
                    topFeature?.feature ||
                    "Feature"
                  )}{" "}
                  is the top contributing feature, accounting for{" "}
                  {formatPercent(topFeature.contributionPercent)} of the total
                  absolute SHAP contribution and{" "}
                  {getShapDirection(topFeature)} the model&apos;s anomaly score.
                </li>
              ) : (
                <li>
                  Detailed SHAP feature contribution is not available for this
                  record.
                </li>
              )}
            </ol>
          </div>
        </div>
      </section>
    </>
  );
}

export default function AnomalyDetail({ record, result, onClose }) {
  if (!record) return null;

  const status = getStatus(record);
  const isAnomaly = status === "Anomaly";
  const explanation = record?.explanation || {};
  const score = Number(record?.anomaly_score);
  const threshold = Number(explanation?.threshold ?? record?.threshold ?? result?.threshold);
  const distance = Number.isFinite(score) && Number.isFinite(threshold) && threshold !== 0
    ? ((score - threshold) / Math.abs(threshold)) * 100
    : null;
  const model = getModelName(result, record, explanation);
  const identifier = getIdentifier(record);

  return (
    <div className="p6-drawer-overlay" onClick={onClose}>
      <aside
        className={`p6-detail-drawer ${isAnomaly ? "p6-detail-anomaly" : "p6-detail-normal"}`}
        onClick={(event) => event.stopPropagation()}
        aria-label={`${status} record explanation`}
      >
        <header className="p6-detail-header-title">
          <div className="p6-detail-status-title">
            <div className="p6-detail-alert-icon">{isAnomaly ? "!" : "✓"}</div>
            <div>
              <h2><span>{isAnomaly ? "ANOMALY" : "NORMAL"}</span><em>—</em>{identifier}</h2>
              <p>Model-generated anomaly investigation</p>
            </div>
          </div>
          <button type="button" className="p6-drawer-close" onClick={onClose} aria-label="Close explanation">×</button>
        </header>

        <section className="p6-executive-premium">
          <div className="p6-detail-executive-grid">
            <div><span>Score</span><strong>{formatScore(score)}</strong></div>
            <div><span>Threshold</span><strong>{formatScore(threshold)}</strong></div>
            <div>
              <span>{isAnomaly ? "Above Threshold" : "Threshold Margin"}</span>
              <strong>
                {distance === null ? "—" : isAnomaly ? `+${formatPercent(distance, 1)}` : `${formatPercent(Math.abs(distance), 1)} below`}
              </strong>
            </div>
            <div><span>Model</span><strong>{model}</strong></div>
          </div>
        </section>

        <ShapFeatureContribution
          record={record}
          explanation={explanation}
          identifier={identifier}
          score={score}
          threshold={threshold}
          isAnomaly={isAnomaly}
        />
      </aside>
    </div>
  );
}
