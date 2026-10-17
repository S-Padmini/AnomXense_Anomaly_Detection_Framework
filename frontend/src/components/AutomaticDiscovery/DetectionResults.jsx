import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

function fmt(value, digits = 4) {
  if (
    value == null ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toLocaleString(
    undefined,
    {
      maximumFractionDigits:
        digits,
    }
  );
}

function Status({ value }) {
  const isAnomaly =
    String(value)
      .toLowerCase() ===
    "anomaly";

  return (
    <span
      className={`ad-status ${
        isAnomaly
          ? "anomaly"
          : "normal"
      }`}
    >
      {value}
    </span>
  );
}

function getModelsUsed(summary) {
  if (
    Array.isArray(
      summary?.models_used
    )
  ) {
    return summary.models_used;
  }

  if (
    Array.isArray(
      summary?.trained_models
    )
  ) {
    return summary.trained_models;
  }

  if (
    Array.isArray(
      summary?.models
    )
  ) {
    return summary.models;
  }

  return [];
}

function getWeights(summary) {
  return (
    summary?.ensemble_weights ||
    summary?.model_weights ||
    {}
  );
}

function getModelDetails(summary) {
  return (
    summary?.model_details ||
    summary?.models_details ||
    summary?.ensemble_models ||
    []
  );
}

export default function DetectionResults({
  api,
  datasetId,
  detection,
  onError,
}) {

  const [result, setResult] =
  useState(null);

const summary =
  result?.summary ||
  detection?.summary ||
  {};

const isUni =
  summary.approach_key ===
    "univariate" ||
  summary.approach ===
    "univariate";

const isCombined =
  summary.score_method ===
    "combined_score" ||
  summary.detection_mode ===
    "combined_ensemble" ||
  summary.mode ===
    "combined_ensemble";

  const [column, setColumn] =
    useState(null);

  const [
    anomaliesOnly,
    setAnomaliesOnly,
  ] = useState(true);

  const [page, setPage] =
    useState(1);

  const [detail, setDetail] =
    useState(null);

  const [chart, setChart] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const columns =
    detection?.column_summaries ||
    [];

  const activeColumn =
    column ||
    columns[0]?.column ||
    null;

  const modelsUsed =
    getModelsUsed(summary);

  const ensembleWeights =
    getWeights(summary);

  const modelDetails =
    getModelDetails(summary);

  useEffect(() => {
    setPage(1);

    setColumn(
      columns[0]?.column ||
        null
    );
  }, [detection?.dataset_id]);

  useEffect(() => {
    let alive = true;

    if (
      !datasetId ||
      !detection
    ) {
      return undefined;
    }

    setLoading(true);

    const load = async () => {
      try {
        const data =
          isUni
            ? await api.columnResult(
                datasetId,
                activeColumn,
                {
                  page,
                  pageSize: 40,
                  anomaliesOnly,
                }
              )
            : await api.result(
                datasetId,
                {
                  page,
                  pageSize: 40,
                  anomaliesOnly,
                }
              );

        const viz =
          await api.visualization(
            datasetId,
            {
              columnName:
                isUni
                  ? activeColumn
                  : null,
              limit: 600,
            }
          );

        if (alive) {
          setResult(data);
          setChart(viz);
        }
      } catch (error) {
        if (alive) {
          onError?.(
            error.message
          );
        }
      } finally {
        if (alive) {
          setLoading(false);
        }
      }
    };

    if (
      !isUni ||
      activeColumn
    ) {
      load();
    }

    return () => {
      alive = false;
    };
  }, [
    api,
    datasetId,
    detection,
    isUni,
    activeColumn,
    page,
    anomaliesOnly,
    onError,
  ]);

  const records =
    result?.records_page
      ?.records || [];

  const pages = Math.max(
    1,
    Number(
      result?.records_page
        ?.total_pages || 1
    )
  );

  const points =
    chart?.points || [];

  const maxScore =
    useMemo(() => {
      const values =
        points.map(
          point =>
            Number(
              point.anomaly_score
            ) || 0
        );

      const threshold =
        Number(
          chart?.threshold
        ) || 1;

      return Math.max(
        ...values,
        threshold,
        1
      );
    }, [points, chart]);

  const openDetail =
    async record => {
      try {
        const data =
          await api.anomaly(
            datasetId,
            record.record_number,
            isUni
              ? activeColumn
              : null
          );

        setDetail(data);
      } catch (error) {
        onError?.(
          error.message
        );
      }
    };

  return (
    <section className="ad-results-wrap">

      <div className="ad-results-header">

        <div>

          <span className="ad-eyebrow">
            04 · DETECTION RESULTS
          </span>

          <h2>
            Detection overview
          </h2>

        </div>

        <div className="ad-result-meta">

          <b>
            {isCombined
              ? "3-Model Ensemble"
              : summary.model ||
                "Selected Model"}
          </b>

          <span>
            {isCombined
              ? "Combined Score"
              : "Best Score"}
          </span>

        </div>

      </div>

      {isCombined && (
        <div
          style={{
            marginBottom:
              "16px",
            padding:
              "16px",
            borderRadius:
              "12px",
            background:
              "#eff6ff",
            border:
              "1px solid #bfdbfe",
          }}
        >

          <div
            style={{
              display:
                "flex",
              alignItems:
                "flex-start",
              gap:
                "10px",
            }}
          >

            <div
              style={{
                fontSize:
                  "20px",
              }}
            >
              ⊕
            </div>

            <div
              style={{
                flex: 1,
              }}
            >

              <strong>
                Combined Ensemble Detection
              </strong>

              <p
                style={{
                  margin:
                    "5px 0 12px",
                  color:
                    "#475569",
                  fontSize:
                    "13px",
                }}
              >
                All recommended models were used
                independently. Their normalized anomaly
                scores were combined using benchmark-based
                weights to produce the final ensemble score.
              </p>

              <div
                style={{
                  display:
                    "flex",
                  flexWrap:
                    "wrap",
                  gap:
                    "8px",
                }}
              >

                {modelsUsed.length > 0
                  ? modelsUsed.map(
                      model => {

                        const weight =
                          ensembleWeights[
                            model
                          ];

                        return (
                          <span
                            key={
                              model
                            }
                            style={{
                              padding:
                                "6px 10px",
                              borderRadius:
                                "999px",
                              background:
                                "#ffffff",
                              border:
                                "1px solid #dbeafe",
                              fontSize:
                                "12px",
                            }}
                          >

                            <strong>
                              {model}
                            </strong>

                            {weight != null && (
                              <>
                                {" "}
                                ·{" "}
                                {(
                                  Number(
                                    weight
                                  ) *
                                  100
                                ).toFixed(
                                  1
                                )}
                                %
                              </>
                            )}

                          </span>
                        );
                      }
                    )
                  : (
                    <span
                      style={{
                        fontSize:
                          "12px",
                        color:
                          "#64748b",
                      }}
                    >
                      Model information will be
                      displayed when returned by
                      the backend.
                    </span>
                  )}

              </div>

            </div>

          </div>

        </div>
      )}

      <div className="ad-overview-grid">

        <div className="ad-kpi">

          <small>
            Total records
          </small>

          <strong>
            {Number(
              summary.total_records ||
                0
            ).toLocaleString()}
          </strong>

        </div>

        <div className="ad-kpi anomaly-kpi">

          <small>
            Anomalies
          </small>

          <strong>
            {Number(
              summary.anomaly_records ||
                0
            ).toLocaleString()}
          </strong>

          <span>
            {fmt(
              summary.anomaly_rate_percent,
              2
            )}
            %
          </span>

        </div>

        <div className="ad-kpi">

          <small>
            Normal
          </small>

          <strong>
            {Number(
              summary.normal_records ||
                0
            ).toLocaleString()}
          </strong>

        </div>

        <div className="ad-kpi">
          <small>
            Accuracy
          </small>

          <strong>
            {summary.accuracy == null
              ? "N/A"
              : `${Number(summary.accuracy).toFixed(2)}%`}
          </strong>
        </div>

        {summary.threshold !=
          null && (
          <div className="ad-kpi">

            <small>
              {isCombined
                ? "Ensemble Threshold"
                : "Threshold"}
            </small>

            <strong>
              {fmt(
                summary.threshold,
                6
              )}
            </strong>

          </div>
        )}

      </div>

      {isCombined &&
        modelDetails.length >
          0 && (

          <div
            className="ad-card"
            style={{
              marginBottom:
                "16px",
            }}
          >

            <div
              className="ad-card-mini-head"
            >

              <div>

                <strong>
                  Model calculation details
                </strong>

                <span>
                  Individual model scores used
                  to form the ensemble
                </span>

              </div>

            </div>

            <div className="ad-table-wrap">

              <table className="ad-table">

                <thead>
                  <tr>
                    <th>
                      Model
                    </th>

                    <th>
                      Benchmark Combined Score
                    </th>

                    <th>
                      Weight
                    </th>

                    <th>
                      Score Normalization
                    </th>
                  </tr>
                </thead>

                <tbody>

                  {modelDetails
                    .slice(0, 3)
                    .map(
                      (item, index) => {

                        const model =
                          item.model ||
                          modelsUsed[
                            index
                          ] ||
                          `Model ${
                            index + 1
                          }`;

                        const benchmarkScore =
                          item.benchmark_score ??
                          item.combined_score;

                        const weight =
                          item.weight ??
                          ensembleWeights[
                            model
                          ];

                        return (
                          <tr
                            key={
                              model
                            }
                          >

                            <td>
                              <strong>
                                {model}
                              </strong>
                            </td>

                            <td>
                              {fmt(
                                benchmarkScore,
                                6
                              )}
                            </td>

                            <td>
                              {weight ==
                              null
                                ? "—"
                                : `${(
                                    Number(
                                      weight
                                    ) *
                                    100
                                  ).toFixed(
                                    1
                                  )}%`}
                            </td>

                            <td>
                              Min-Max
                              normalization
                            </td>

                          </tr>
                        );
                      }
                    )}

                </tbody>

              </table>

            </div>

          </div>
        )}

      {isUni &&
        columns.length >
          0 && (

          <div className="ad-column-tabs">

            {columns.map(item => (

              <button
                type="button"
                key={
                  item.column
                }
                className={
                  activeColumn ===
                  item.column
                    ? "is-active"
                    : ""
                }
                onClick={() => {
                  setColumn(
                    item.column
                  );
                  setPage(1);
                }}
              >

                {item.column}

                <span>
                  {item.anomaly_records}
                </span>

              </button>

            ))}

          </div>
        )}

      <div className="ad-result-grid">

        <div className="ad-card ad-chart-card">

          <div className="ad-card-mini-head">

            <div>

              <strong>
                {isCombined
                  ? "Ensemble score distribution"
                  : "Score distribution"}
              </strong>

              <span>
                {isCombined
                  ? "Final weighted ensemble anomaly scores"
                  : "Actual fitted-model anomaly scores"}
              </span>

            </div>

            {chart?.sampling_applied && (
              <small>
                Sampled for display
              </small>
            )}

          </div>

          <div className="ad-chart">

            {points.length ===
            0 ? (

              <div className="ad-empty">
                No visualization points
                available.
              </div>

            ) : (

              points.map(
                point => {

                  const height =
                    Math.max(
                      3,
                      (
                        Number(
                          point.anomaly_score
                        ) /
                        maxScore
                      ) *
                        100
                    );

                  return (

                    <button
                      key={
                        point.record_number
                      }
                      title={`Record ${
                        point.record_number
                      }: ${fmt(
                        point.anomaly_score
                      )}`}
                      className={`ad-bar ${
                        point.status ===
                        "Anomaly"
                          ? "is-anomaly"
                          : ""
                      }`}
                      style={{
                        height: `${height}%`,
                      }}
                      onClick={() =>
                        openDetail({
                          record_number:
                            point.record_number,
                        })
                      }
                    />

                  );
                }
              )

            )}

          </div>

          <div className="ad-chart-axis">

            <span>
              Lower score
            </span>

            <span>
              {isCombined
                ? "Ensemble threshold "
                : "Threshold "}
              {fmt(
                chart?.threshold,
                6
              )}
            </span>

            <span>
              Higher score
            </span>

          </div>

        </div>

        <div className="ad-card ad-records-card">

          <div className="ad-card-mini-head">

            <div>

              <strong>
                {isUni
                  ? `Records · ${activeColumn}`
                  : "Records"}
              </strong>

              <span>
                {result?.records_page
                  ?.total_matching_records ??
                  0}{" "}
                matching records
              </span>

            </div>

            <label className="ad-toggle">

              <input
                type="checkbox"
                checked={
                  anomaliesOnly
                }
                onChange={e => {
                  setAnomaliesOnly(
                    e.target.checked
                  );
                  setPage(1);
                }}
              />

              <span />

              anomalies only

            </label>

          </div>

          {loading ? (

            <div className="ad-loading-row">

              <span className="ad-spinner" />

              Loading records…

            </div>

          ) : (

            <div className="ad-table-wrap">

              <table className="ad-table ad-record-table">

                <thead>

                  <tr>

                    <th>
                      Record
                    </th>

                    <th>
                      Status
                    </th>

                    <th>
                      {isCombined
                        ? "Ensemble Score"
                        : "Score"}
                    </th>

                    <th>
                      Threshold
                    </th>

                    <th />

                  </tr>

                </thead>

                <tbody>

                  {records.map(
                    record => (

                      <tr
                        key={
                          record.record_number
                        }
                      >

                        <td>
                          #
                          {
                            record.record_number
                          }
                        </td>

                        <td>
                          <Status
                            value={
                              record.status
                            }
                          />
                        </td>

                        <td>
                          {fmt(
                            record.anomaly_score
                          )}
                        </td>

                        <td>
                          {fmt(
                            record.threshold,
                            6
                          )}
                        </td>

                        <td>

                          <button
                            className="ad-link-btn"
                            onClick={() =>
                              openDetail(
                                record
                              )
                            }
                          >
                            View
                          </button>

                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>

              {records.length ===
                0 && (
                <div className="ad-empty">
                  No records match the
                  current filter.
                </div>
              )}

            </div>

          )}

          <div className="ad-pagination">

            <button
              disabled={
                page <= 1
              }
              onClick={() =>
                setPage(
                  current =>
                    current - 1
                )
              }
            >
              ‹
            </button>

            <span>
              Page {page} of{" "}
              {pages}
            </span>

            <button
              disabled={
                page >= pages
              }
              onClick={() =>
                setPage(
                  current =>
                    current + 1
                )
              }
            >
              ›
            </button>

          </div>

        </div>

      </div>

      {detail && (

        <div
          className="ad-detail-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() =>
            setDetail(null)
          }
        >

          <div
            className="ad-detail-panel"
            onClick={event =>
              event.stopPropagation()
            }
          >

            <div className="ad-detail-head">

              <div>

                <span className="ad-eyebrow">
                  RECORD DETAIL
                </span>

                <h3>
                  Record #
                  {
                    detail.record_number
                  }
                </h3>

              </div>

              <button
                onClick={() =>
                  setDetail(null)
                }
              >
                ×
              </button>

            </div>

            <div className="ad-detail-kpis">

              <div>

                <small>
                  Status
                </small>

                <Status
                  value={
                    detail.status
                  }
                />

              </div>

              <div>

                <small>
                  {isCombined
                    ? "Ensemble Score"
                    : "Score"}
                </small>

                <strong>
                  {fmt(
                    detail.anomaly_score,
                    8
                  )}
                </strong>

              </div>

              <div>

                <small>
                  {isCombined
                    ? "Ensemble Threshold"
                    : "Threshold"}
                </small>

                <strong>
                  {fmt(
                    detail.threshold,
                    8
                  )}
                </strong>

              </div>

            </div>

            {isCombined &&
              detail.model_scores && (

                <div
                  style={{
                    marginTop:
                      "16px",
                    padding:
                      "14px",
                    background:
                      "#f8fafc",
                    borderRadius:
                      "10px",
                  }}
                >

                  <strong>
                    Individual model scores
                  </strong>

                  <div
                    style={{
                      marginTop:
                        "10px",
                      display:
                        "grid",
                      gap:
                        "8px",
                    }}
                  >

                    {Object.entries(
                      detail.model_scores
                    ).map(
                      ([model, value]) => (

                        <div
                          key={
                            model
                          }
                          style={{
                            display:
                              "flex",
                            justifyContent:
                              "space-between",
                            padding:
                              "8px 10px",
                            background:
                              "#fff",
                            border:
                              "1px solid #e2e8f0",
                            borderRadius:
                              "8px",
                          }}
                        >

                          <strong>
                            {model}
                          </strong>

                          <span>
                            {typeof value ===
                            "object"
                              ? fmt(
                                  value?.normalized_score ??
                                    value?.raw_score
                                )
                              : fmt(
                                  value
                                )}
                          </span>

                        </div>

                      )
                    )}

                  </div>

                </div>
              )}

            <p className="ad-note">
              {detail.explanation}
            </p>

            <div className="ad-values">

              {Object.entries(
                detail.values || {}
              ).map(
                ([key, value]) => (

                  <div key={key}>

                    <span>
                      {key}
                    </span>

                    <strong>
                      {String(
                        value ??
                          "—"
                      )}
                    </strong>

                  </div>

                )
              )}

            </div>

          </div>

        </div>

      )}

    </section>
  );
}