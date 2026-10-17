import React from "react";

const methodInfo = {
  best_score: {
    label: "Best Score",
    text:
      "Select one of the three recommended models. Only that model will be used for final anomaly detection.",
  },

  combined_score: {
    label: "Combined Score",
    text:
      "All three recommended models are used together. Their anomaly scores are normalized and combined using benchmark-based model weights.",
  },
};

function pct(value) {
  return value == null ||
    Number.isNaN(Number(value))
    ? "—"
    : `${(
        Number(value) * 100
      ).toFixed(1)}%`;
}

function score(value) {
  return value == null ||
    Number.isNaN(Number(value))
    ? "—"
    : Number(value).toFixed(3);
}

function ms(value) {
  return value == null
    ? "—"
    : `${Number(value).toFixed(1)} ms`;
}

function getBenchmarkScore(item) {
  return (
    item?.combined_score ??
    item?.benchmark_score ??
    item?.score ??
    null
  );
}

function calculateWeights(recommendations) {
  const valid = recommendations
    .slice(0, 3)
    .map(item => ({
      model: item.model,
      score: Number(
        getBenchmarkScore(item)
      ),
    }))
    .filter(
      item =>
        Number.isFinite(item.score) &&
        item.score >= 0
    );

  const total = valid.reduce(
    (sum, item) =>
      sum + item.score,
    0
  );

  if (!total) {
    return {};
  }

  return valid.reduce(
    (result, item) => {
      result[item.model] =
        item.score / total;

      return result;
    },
    {}
  );
}

export default function ModelRecommendation({
  recommendations = [],
  scoreMethod,
  onScoreMethodChange,
  selectedModel,
  onModelChange,
  loading = false,
  disabled = false,
}) {
  const info =
    methodInfo[scoreMethod] ||
    methodInfo.combined_score;

  const isCombined =
    scoreMethod === "combined_score";

  const topThree =
    recommendations.slice(0, 3);

  const ensembleWeights =
    calculateWeights(topThree);

  function handleModelClick(model) {
    /*
     * Combined mode intentionally does NOT allow
     * one-model selection.
     */
    if (isCombined) {
      return;
    }

    onModelChange(model);
  }

  return (
    <section className="ad-card">

      <div className="ad-section-head ad-section-head-row">

        <div>

          <span className="ad-eyebrow">
            02 · MODEL RECOMMENDATION
          </span>

          <h2>
            Empirically benchmarked candidates
          </h2>

          <p>
            Only successfully benchmarked models
            are shown. The ranking is a model-selection
            signal, not ground-truth accuracy.
          </p>

        </div>

        <label className="ad-select-wrap">

          <span>
            Scoring method
          </span>

          <select
            value={scoreMethod}
            onChange={e =>
              onScoreMethodChange(
                e.target.value
              )
            }
            disabled={
              disabled ||
              loading
            }
          >

            <option value="combined_score">
              Combined Score
            </option>

            <option value="best_score">
              Best Score
            </option>

          </select>

        </label>

      </div>

      <div className="ad-info-strip">

        <strong>
          {info.label}:
        </strong>{" "}

        {info.text}

      </div>

      {loading ? (

        <div className="ad-loading-row">

          <span className="ad-spinner" />

          Loading benchmark recommendations…

        </div>

      ) : topThree.length === 0 ? (

        <div className="ad-empty">
          No successful recommendations
          are available yet.
        </div>

      ) : (

        <>

          <div className="ad-model-list">

            {topThree.map(
              (item, index) => {

                const rank =
                  item.rank ||
                  index + 1;

                const active =
                  !isCombined &&
                  selectedModel ===
                    item.model;

                const benchmarkScore =
                  getBenchmarkScore(item);

                const ensembleWeight =
                  ensembleWeights[
                    item.model
                  ];

                return (

                  <button
                    type="button"
                    key={item.model}
                    className={`ad-model-row ${
                      active
                        ? "is-selected"
                        : ""
                    } ${
                      isCombined
                        ? "is-ensemble-model"
                        : ""
                    }`}
                    onClick={() =>
                      handleModelClick(
                        item.model
                      )
                    }
                    disabled={
                      disabled ||
                      isCombined
                    }
                  >

                    <span className="ad-rank">
                      #{rank}
                    </span>

                    <span className="ad-model-main">

                      <strong>
                        {item.model}
                      </strong>

                      <span>
                        {item.successful_runs}
                        /
                        {item.attempted_runs}
                        {" "}
                        successful runs
                      </span>

                      {isCombined && (
                        <small
                          style={{
                            marginTop:
                              "4px",
                            color:
                              "#2563eb",
                            fontWeight:
                              700,
                          }}
                        >
                          Included in ensemble
                        </small>
                      )}

                    </span>

                    <span className="ad-metric">

                      <small>
                        {info.label}
                      </small>

                      <strong>
                        {score(
                          item[
                            scoreMethod
                          ]
                        )}
                      </strong>

                    </span>

                    <span className="ad-metric">

                      <small>
                        Stability
                      </small>

                      <strong>
                        {pct(
                          item.stability_score
                        )}
                      </strong>

                    </span>

                    <span className="ad-metric">

                      <small>
                        Runtime
                      </small>

                      <strong>
                        {ms(
                          item.runtime_ms
                        )}
                      </strong>

                    </span>

                    {isCombined ? (

                      <span
                        className="ad-metric"
                      >

                        <small>
                          Ensemble Weight
                        </small>

                        <strong>
                          {ensembleWeight ==
                          null
                            ? "—"
                            : `${(
                                ensembleWeight *
                                100
                              ).toFixed(1)}%`}
                        </strong>

                      </span>

                    ) : (

                      <span
                        className="ad-radio"
                        aria-hidden="true"
                      />

                    )}

                  </button>

                );
              }
            )}

          </div>

          {isCombined && (
            <div
              style={{
                marginTop: "16px",
                padding: "16px",
                borderRadius: "12px",
                border:
                  "1px solid #bfdbfe",
                background:
                  "#eff6ff",
              }}
            >

              <div
                style={{
                  display: "flex",
                  alignItems:
                    "flex-start",
                  gap: "10px",
                }}
              >

                <div
                  style={{
                    fontSize: "20px",
                  }}
                >
                  ⊕
                </div>

                <div>

                  <strong>
                    Combined Ensemble Mode
                  </strong>

                  <p
                    style={{
                      margin:
                        "5px 0 0",
                      color:
                        "#475569",
                      fontSize:
                        "13px",
                      lineHeight:
                        1.5,
                    }}
                  >
                    All {topThree.length} recommended
                    models will be trained independently.
                    Each model produces anomaly scores for
                    the records. The scores are normalized,
                    weighted using the benchmark Combined
                    Scores, and combined into one final
                    ensemble score.
                  </p>

                </div>

              </div>

              <div
                style={{
                  marginTop:
                    "12px",
                  display:
                    "flex",
                  flexWrap:
                    "wrap",
                  gap:
                    "8px",
                }}
              >

                {topThree.map(
                  item => {

                    const weight =
                      ensembleWeights[
                        item.model
                      ];

                    return (
                      <span
                        key={
                          item.model
                        }
                        style={{
                          display:
                            "inline-flex",
                          alignItems:
                            "center",
                          gap:
                            "6px",
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
                          {item.model}
                        </strong>

                        <span>
                          {weight == null
                            ? "—"
                            : `${(
                                weight *
                                100
                              ).toFixed(1)}%`}
                        </span>

                      </span>
                    );

                  }
                )}

              </div>

            </div>
          )}

          {!isCombined && (
            <div
              className="ad-info-strip"
              style={{
                marginTop:
                  "12px",
              }}
            >

              {selectedModel ? (

                <>
                  <strong>
                    Selected model:
                  </strong>{" "}
                  {selectedModel}
                  <br />

                  <span
                    style={{
                      fontSize:
                        "12px",
                    }}
                  >
                    Only this model will be
                    used for final detection.
                  </span>
                </>

              ) : (

                <>
                  <strong>
                    Select one model
                  </strong>{" "}
                  from the three recommended
                  candidates to continue.
                </>

              )}

            </div>
          )}

        </>

      )}

    </section>
  );
}