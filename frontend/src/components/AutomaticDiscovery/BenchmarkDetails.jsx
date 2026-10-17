import React, { useState } from "react";

function pct(value) {
  return value == null || Number.isNaN(Number(value))
    ? "—"
    : `${(Number(value) * 100).toFixed(1)}%`;
}

function score(value) {
  return value == null || Number.isNaN(Number(value))
    ? "—"
    : Number(value).toFixed(3);
}

function weightPct(value) {
  return value == null || Number.isNaN(Number(value))
    ? "—"
    : `${(Number(value) * 100).toFixed(1)}%`;
}

function modelLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, char => char.toUpperCase());
}

export default function BenchmarkDetails({
  benchmark,
  warning,
}) {
  const [open, setOpen] = useState(false);

  if (!benchmark) {
    return null;
  }

  const metrics = benchmark.metrics || {};
  const weights = metrics.weights || {};
  const rows = Array.isArray(benchmark.results)
    ? benchmark.results
    : [];

  /*
   * The backend may eventually return the fixed Top 3
   * under one of these fields.
   *
   * We support all common shapes without breaking the
   * existing benchmark response.
   */
  const topThree =
    benchmark.top_three_recommendations ||
    benchmark.top_three ||
    benchmark.recommendations ||
    rows.filter(row => row.rank && Number(row.rank) <= 3);

  const ensembleWeights =
    benchmark.ensemble_weights ||
    benchmark.model_weights ||
    {};

  return (
    <section className="ad-card ad-benchmark-card">

      <button
        type="button"
        className="ad-collapse-head"
        onClick={() => setOpen(value => !value)}
      >
        <span>
          <span className="ad-eyebrow">
            BENCHMARK DETAILS
          </span>

          <strong>
            How were the models compared?
          </strong>
        </span>

        <span className="ad-collapse-arrow">
          {open ? "−" : "+"}
        </span>
      </button>

      {open && (
        <div className="ad-benchmark-body">

          <div className="ad-benchmark-summary">

            <div>
              <small>Method</small>
              <strong>
                {benchmark.benchmark_method || "Empirical Benchmark"}
              </strong>
            </div>

            <div>
              <small>Rows evaluated</small>
              <strong>
                {benchmark.benchmark_rows?.toLocaleString?.() ??
                  benchmark.benchmark_rows ??
                  "—"}
              </strong>
            </div>

            <div>
              <small>Repeats / unit</small>
              <strong>
                {benchmark.repeats_per_model_per_unit ?? "—"}
              </strong>
            </div>

            <div>
              <small>Benchmark contamination</small>
              <strong>
                {Number(
                  benchmark.benchmark_contamination ?? 0.10
                ).toFixed(2)}
              </strong>
            </div>

          </div>

          {(warning || metrics.warning) && (
            <p className="ad-note">
              {warning || metrics.warning}
            </p>
          )}

          <div className="ad-weight-row">
            {Object.entries(weights).map(([key, value]) => (
              <span key={key}>
                <b>
                  {modelLabel(
                    key.replace("_score", "")
                  )}
                </b>{" "}
                {Math.round(Number(value) * 100)}%
              </span>
            ))}
          </div>

          <div className="ad-table-wrap">

            <table className="ad-table">

              <thead>
                <tr>
                  <th>Model</th>
                  <th>Combined</th>
                  <th>Best</th>
                  <th>Stability</th>
                  <th>Agreement</th>
                  <th>Reliability</th>
                </tr>
              </thead>

              <tbody>

                {rows.map(row => (
                  <tr key={row.model}>

                    <td>
                      <strong>
                        {row.model}
                      </strong>
                    </td>

                    <td>
                      {score(row.combined_score)}
                    </td>

                    <td>
                      {score(row.best_score)}
                    </td>

                    <td>
                      {pct(row.stability_score)}
                    </td>

                    <td>
                      {pct(row.agreement_score)}
                    </td>

                    <td>
                      {pct(row.reliability_score)}
                    </td>

                  </tr>
                ))}

              </tbody>

            </table>

          </div>

          {Array.isArray(topThree) &&
            topThree.length > 0 && (
              <div
                style={{
                  marginTop: "18px",
                  padding: "16px",
                  border: "1px solid #e2e8f0",
                  borderRadius: "12px",
                  background: "#f8fafc",
                }}
              >

                <div
                  style={{
                    marginBottom: "12px",
                  }}
                >
                  <strong>
                    Combined Ensemble — Top 3 Models
                  </strong>

                  <p
                    style={{
                      margin: "5px 0 0",
                      fontSize: "13px",
                      color: "#64748b",
                    }}
                  >
                    In Combined Score mode, all three
                    recommended models are used together.
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(150px, 1fr))",
                    gap: "10px",
                  }}
                >

                  {topThree.slice(0, 3).map((item, index) => {

                    const model =
                      item?.model ||
                      item?.name ||
                      `Model ${index + 1}`;

                    const benchmarkScore =
                      item?.combined_score ??
                      item?.benchmark_score ??
                      item?.score;

                    const weight =
                      ensembleWeights[model] ??
                      item?.ensemble_weight ??
                      item?.weight;

                    return (
                      <div
                        key={model}
                        style={{
                          background: "#ffffff",
                          border: "1px solid #e2e8f0",
                          borderRadius: "10px",
                          padding: "12px",
                        }}
                      >

                        <div
                          style={{
                            fontSize: "12px",
                            color: "#64748b",
                          }}
                        >
                          Model #{index + 1}
                        </div>

                        <strong>
                          {model}
                        </strong>

                        <div
                          style={{
                            marginTop: "8px",
                            fontSize: "13px",
                          }}
                        >
                          <div>
                            Benchmark:{" "}
                            <b>
                              {score(benchmarkScore)}
                            </b>
                          </div>

                          <div>
                            Ensemble weight:{" "}
                            <b>
                              {weightPct(weight)}
                            </b>
                          </div>
                        </div>

                      </div>
                    );
                  })}

                </div>

              </div>
            )}

          {benchmark.errors?.length > 0 && (
            <div className="ad-error-note">
              {benchmark.errors.length} model/unit benchmark
              events did not complete successfully. Failed
              candidates are not silently substituted.
            </div>
          )}

        </div>
      )}

    </section>
  );
}