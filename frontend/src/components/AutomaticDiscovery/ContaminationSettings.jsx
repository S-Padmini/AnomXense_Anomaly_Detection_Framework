import React from "react";

function clamp(value) {
  return Math.min(
    0.50,
    Math.max(
      0.01,
      Number(value) || 0.10
    )
  );
}

export default function ContaminationSettings({
  mode,
  value,
  onModeChange,
  onChange,
  disabled = false,
  scoreMethod = "best_score",
}) {
  const custom = mode === "custom";

  const setValue = next => {
    onChange(
      Number(
        clamp(next).toFixed(2)
      )
    );
  };

  const isCombined =
    scoreMethod === "combined_score";

  return (
    <section className="ad-card">

      <div className="ad-section-head">

        <div>

          <span className="ad-eyebrow">
            03 · CONTAMINATION SETTINGS
          </span>

          <h2>
            Expected anomaly proportion
          </h2>

          <p>
            {isCombined
              ? "This value is used to determine the final anomaly threshold from the combined ensemble score."
              : "This value is applied when the selected model is fitted for final detection."}
          </p>

        </div>

      </div>

      <div className="ad-contamination-grid">

        <button
          type="button"
          className={`ad-setting-option ${
            !custom ? "is-selected" : ""
          }`}
          onClick={() =>
            onModeChange("default")
          }
          disabled={disabled}
        >

          <span className="ad-setting-title">

            <strong>
              Default
            </strong>

            <b>
              0.10
            </b>

          </span>

          <small>
            Uses the framework default of 10%.
          </small>

        </button>

        <button
          type="button"
          className={`ad-setting-option ${
            custom ? "is-selected" : ""
          }`}
          onClick={() =>
            onModeChange("custom")
          }
          disabled={disabled}
        >

          <span className="ad-setting-title">

            <strong>
              Custom
            </strong>

            <b>
              {Number(value).toFixed(2)}
            </b>

          </span>

          <small>
            Choose a value between 0.01 and 0.50.
          </small>

        </button>

      </div>

      {custom && (
        <div className="ad-stepper">

          <button
            type="button"
            onClick={() =>
              setValue(value - 0.01)
            }
            disabled={
              disabled ||
              value <= 0.01
            }
          >
            −
          </button>

          <div>

            <strong>
              {Number(value).toFixed(2)}
            </strong>

            <span>
              {Math.round(
                Number(value) * 100
              )}
              %
            </span>

          </div>

          <button
            type="button"
            onClick={() =>
              setValue(value + 0.01)
            }
            disabled={
              disabled ||
              value >= 0.50
            }
          >
            +
          </button>

        </div>
      )}

      <div
        style={{
          marginTop: "12px",
          fontSize: "12px",
          color: "#64748b",
        }}
      >
        {isCombined
          ? "Combined mode: the three recommended models contribute to one ensemble score, and this contamination value controls the final ensemble threshold."
          : "Best Score mode: the selected model determines the anomaly score and threshold."}
      </div>

    </section>
  );
}