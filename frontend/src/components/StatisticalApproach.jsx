
import React, { useState } from "react";

function StatisticalApproach({
  datasetId,
  onSelectApproach,
  onBack,
}) {
  const [selectedApproach, setSelectedApproach] =
    useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleContinue = async () => {
    if (!selectedApproach) {
      setError(
        "Please select a statistical approach."
      );
      return;
    }

    setError("");
    setLoading(true);

    try {
      if (!onSelectApproach) {
        throw new Error(
          "Unable to start preprocessing. Please try again."
        );
      }

      // Keep the loading state active while the parent runs preprocessing.
      // Some parent callbacks start the async backend work without returning
      // its Promise, so a finally block here would reset the button too early.
      await onSelectApproach(
        selectedApproach,
        datasetId
      );

      // Do not reset loading on success. The parent should navigate to the
      // results view when preprocessing completes, which unmounts this screen.
    } catch (err) {
      setLoading(false);
      setError(
        err?.message ||
          "Unable to start preprocessing. Please try again."
      );
    }
  };

  return (
    <div className="statistical-approach-page">
      <style>{`
        * {
          box-sizing: border-box;
        }

        .statistical-approach-page {
          min-height: 100%;
          padding: 24px;
          background:
            linear-gradient(
              180deg,
              #eef2ff 0%,
              #f6f7fc 55%,
              #fafbfe 100%
            );
          color: #17213f;
          font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
        }

        .statistical-approach-container {
          width: min(1080px, 100%);
          margin: 0 auto;
        }

        /* --------------------------------
           HEADER
        -------------------------------- */

        .statistical-approach-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          padding: 20px 22px;
          margin-bottom: 14px;

          background:
            linear-gradient(
              135deg,
              #17255f 0%,
              #293b8f 58%,
              #4257ad 100%
            );

          border: 1px solid
            rgba(41, 59, 143, 0.25);

          border-radius: 14px;

          box-shadow:
            0 12px 28px
              rgba(31, 47, 111, 0.18);
        }

        .statistical-header-left {
          min-width: 0;
        }

        .statistical-approach-header h1 {
          margin: 0;
          color: #ffffff;
          font-size: 27px;
          line-height: 1.2;
          font-weight: 800;
          letter-spacing: -0.3px;
        }

        .statistical-approach-header p {
          margin: 7px 0 0;
          color: rgba(255, 255, 255, 0.78);
          font-size: 15px;
          line-height: 1.45;
        }

        .statistical-back-button {
          flex-shrink: 0;

          border: 1px solid
            rgba(255, 255, 255, 0.38);

          background:
            rgba(255, 255, 255, 0.09);

          color: #ffffff;

          border-radius: 8px;
          padding: 9px 15px;

          font-size: 14px;
          font-weight: 750;

          cursor: pointer;

          transition:
            background 0.18s ease,
            border-color 0.18s ease,
            transform 0.18s ease;
        }

        .statistical-back-button:hover:not(:disabled) {
          background:
            rgba(255, 255, 255, 0.17);

          border-color:
            rgba(255, 255, 255, 0.65);

          transform: translateY(-1px);
        }

        .statistical-back-button:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        /* --------------------------------
           DATASET STRIP
        -------------------------------- */

        .statistical-dataset-info {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 15px;

          padding: 11px 15px;
          margin-bottom: 16px;

          background: #ffffff;

          border: 1px solid #d9e0f0;
          border-radius: 10px;

          box-shadow:
            0 4px 14px
              rgba(32, 48, 110, 0.05);
        }

        .statistical-info-label {
          color: #66718c;
          font-size: 13px;
          font-weight: 750;
          text-transform: uppercase;
          letter-spacing: 0.7px;
        }

        .statistical-info-value {
          max-width: 70%;

          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;

          padding: 5px 10px;

          border-radius: 7px;

          background: #eef1ff;
          color: #293b8f;

          font-size: 14px;
          font-weight: 800;
        }

        /* --------------------------------
           SECTION INTRO
        -------------------------------- */

        .statistical-selection-panel {
          padding: 19px;

          background: #ffffff;

          border: 1px solid #d9e0f0;
          border-radius: 14px;

          box-shadow:
            0 7px 22px
              rgba(27, 43, 94, 0.07);
        }

        .statistical-selection-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;

          margin-bottom: 14px;
        }

        .statistical-selection-title {
          margin: 0;

          color: #18265f;

          font-size: 20px;
          font-weight: 800;
        }

        .statistical-selection-subtitle {
          margin: 4px 0 0;

          color: #66718c;

          font-size: 14px;
          line-height: 1.4;
        }

        .statistical-selection-hint {
          flex-shrink: 0;

          padding: 6px 10px;

          border: 1px solid #d9e0f0;
          border-radius: 999px;

          background: #f7f8fd;
          color: #66718c;

          font-size: 12px;
          font-weight: 750;
        }

        /* --------------------------------
           APPROACH CARDS
        -------------------------------- */

        .statistical-approach-options {
          display: grid;
          grid-template-columns:
            repeat(2, minmax(0, 1fr));

          gap: 14px;
        }

        .statistical-approach-card {
          position: relative;

          display: grid;
          grid-template-columns:
            46px minmax(0, 1fr) 22px;

          align-items: center;

          gap: 14px;

          width: 100%;
          min-height: 142px;

          padding: 17px;

          text-align: left;

          background: #ffffff;

          border: 1.5px solid #d9e0f0;
          border-radius: 12px;

          color: #17213f;

          cursor: pointer;

          transition:
            border-color 0.18s ease,
            box-shadow 0.18s ease,
            transform 0.18s ease,
            background 0.18s ease;
        }

        .statistical-approach-card:hover:not(:disabled) {
          border-color: #4257ad;

          background: #fbfcff;

          box-shadow:
            0 9px 22px
              rgba(41, 59, 143, 0.13);

          transform: translateY(-2px);
        }

        .statistical-approach-card.selected {
          border-color: #293b8f;

          background:
            linear-gradient(
              135deg,
              #f7f8ff 0%,
              #eef1ff 100%
            );

          box-shadow:
            0 0 0 2px
              rgba(41, 59, 143, 0.12),
            0 10px 24px
              rgba(41, 59, 143, 0.14);
        }

        .statistical-approach-card:disabled {
          cursor: not-allowed;
          opacity: 0.65;
        }

        /* --------------------------------
           CARD ICON
        -------------------------------- */

        .statistical-card-icon {
          display: flex;
          align-items: center;
          justify-content: center;

          width: 46px;
          height: 46px;

          border-radius: 11px;

          background:
            linear-gradient(
              135deg,
              #293b8f,
              #4257ad
            );

          color: #ffffff;

          font-size: 19px;
          font-weight: 850;

          box-shadow:
            0 5px 12px
              rgba(41, 59, 143, 0.18);
        }

        .statistical-approach-card.selected
          .statistical-card-icon {
          background:
            linear-gradient(
              135deg,
              #18265f,
              #293b8f
            );
        }

        /* --------------------------------
           CARD CONTENT
        -------------------------------- */

        .statistical-card-content {
          min-width: 0;
        }

        .statistical-card-content h2 {
          margin: 0 0 5px;

          color: #18265f;

          font-size: 19px;
          line-height: 1.2;
          font-weight: 800;
        }

        .statistical-card-content p {
          margin: 0 0 10px;

          color: #66718c;

          font-size: 13.5px;
          line-height: 1.45;
        }

        .statistical-card-method {
          display: inline-flex;
          align-items: center;
          gap: 7px;

          padding: 5px 9px;

          border: 1px solid #dce2f1;
          border-radius: 6px;

          background: #f7f8fd;

          color: #66718c;

          font-size: 11px;
          font-weight: 750;
          text-transform: uppercase;
          letter-spacing: 0.45px;
        }

        .statistical-card-method strong {
          color: #293b8f;

          font-size: 12px;
          font-weight: 850;

          text-transform: none;
          letter-spacing: 0;
        }

        /* --------------------------------
           RADIO / SELECT INDICATOR
        -------------------------------- */

        .statistical-card-radio {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .radio {
          display: block;

          width: 18px;
          height: 18px;

          border: 2px solid #b7c0d6;
          border-radius: 50%;

          background: #ffffff;

          transition:
            border-color 0.18s ease,
            box-shadow 0.18s ease,
            background 0.18s ease;
        }

        .radio.selected {
          border-color: #293b8f;

          background:
            radial-gradient(
              circle,
              #293b8f 0 42%,
              #ffffff 45% 100%
            );

          box-shadow:
            0 0 0 3px
              rgba(41, 59, 143, 0.10);
        }

        /* --------------------------------
           ERROR
        -------------------------------- */

        .statistical-approach-error {
          margin-top: 13px;

          padding: 10px 13px;

          border: 1px solid #f1c4cd;
          border-left: 4px solid #c52b48;

          border-radius: 8px;

          background: #fff3f5;
          color: #a8223b;

          font-size: 13px;
          font-weight: 650;
        }

        /* --------------------------------
           ACTION BAR
        -------------------------------- */

        .statistical-approach-actions {
          display: flex;
          justify-content: flex-end;
          align-items: center;

          gap: 10px;

          margin-top: 15px;
        }

        .statistical-continue-button {
          min-width: 125px;

          border: 1px solid #293b8f;
          border-radius: 8px;

          padding: 10px 18px;

          background:
            linear-gradient(
              135deg,
              #293b8f,
              #4257ad
            );

          color: #ffffff;

          font-size: 14px;
          font-weight: 800;

          cursor: pointer;

          box-shadow:
            0 5px 13px
              rgba(41, 59, 143, 0.18);

          transition:
            transform 0.18s ease,
            box-shadow 0.18s ease,
            background 0.18s ease;
        }

        .statistical-continue-button:hover:not(:disabled) {
          background:
            linear-gradient(
              135deg,
              #18265f,
              #293b8f
            );

          transform: translateY(-1px);

          box-shadow:
            0 8px 18px
              rgba(41, 59, 143, 0.24);
        }

        .statistical-continue-button:disabled {
          background: #c5cad8;
          border-color: #c5cad8;

          box-shadow: none;

          cursor: not-allowed;
        }

        /* --------------------------------
           RESPONSIVE
        -------------------------------- */

        @media (max-width: 760px) {
          .statistical-approach-page {
            padding: 14px;
          }

          .statistical-approach-header {
            padding: 17px;
          }

          .statistical-approach-header h1 {
            font-size: 23px;
          }

          .statistical-approach-header p {
            font-size: 13px;
          }

          .statistical-approach-options {
            grid-template-columns: 1fr;
          }

          .statistical-selection-panel {
            padding: 14px;
          }

          .statistical-selection-heading {
            align-items: flex-start;
            flex-direction: column;
          }

          .statistical-selection-hint {
            display: none;
          }
        }
      `}</style>

      <div className="statistical-approach-container">

        {/* Header */}
        <div className="statistical-approach-header">
          <div className="statistical-header-left">
            <h1>
              Statistical Approach
            </h1>

            <p>
              Choose how the preprocessed dataset
              should be analyzed for anomalies.
            </p>
          </div>

          {onBack && (
            <button
              type="button"
              className="statistical-back-button"
              onClick={onBack}
              disabled={loading}
            >
              ← Back
            </button>
          )}
        </div>

        {/* Dataset */}
        {datasetId && (
          <div className="statistical-dataset-info">
            <span className="statistical-info-label">
              Current Dataset
            </span>

            <span className="statistical-info-value">
              {datasetId}
            </span>
          </div>
        )}

        {/* Selection panel */}
        <div className="statistical-selection-panel">

          <div className="statistical-selection-heading">
            <div>
              <h2 className="statistical-selection-title">
                Select Analysis Method
              </h2>

              <p className="statistical-selection-subtitle">
                Select one approach to continue with
                statistical anomaly detection.
              </p>
            </div>

            <span className="statistical-selection-hint">
              Select one
            </span>
          </div>

          {/* Approach cards */}
          <div className="statistical-approach-options">

            {/* Univariate */}
            <button
              type="button"
              className={`statistical-approach-card ${
                selectedApproach ===
                "univariate"
                  ? "selected"
                  : ""
              }`}
              onClick={() => {
                setSelectedApproach(
                  "univariate"
                );
                setError("");
              }}
              disabled={loading}
            >
              <div className="statistical-card-icon">
                U
              </div>

              <div className="statistical-card-content">
                <h2>
                  Univariate
                </h2>

                <p>
                  Analyze each numerical column
                  independently to identify
                  individual feature outliers.
                </p>

                <div className="statistical-card-method">
                  Method
                  <strong>
                    IQR
                  </strong>
                </div>
              </div>

              <div className="statistical-card-radio">
                <span
                  className={
                    selectedApproach ===
                    "univariate"
                      ? "radio selected"
                      : "radio"
                  }
                />
              </div>
            </button>

            {/* Multivariate */}
            <button
              type="button"
              className={`statistical-approach-card ${
                selectedApproach ===
                "multivariate"
                  ? "selected"
                  : ""
              }`}
              onClick={() => {
                setSelectedApproach(
                  "multivariate"
                );
                setError("");
              }}
              disabled={loading}
            >
              <div className="statistical-card-icon">
                M
              </div>

              <div className="statistical-card-content">
                <h2>
                  Multivariate
                </h2>

                <p>
                  Analyze the combined behavior of
                  selected features using their
                  multivariate relationships.
                </p>

                <div className="statistical-card-method">
                  Method
                  <strong>
                    Mahalanobis Distance
                  </strong>
                </div>
              </div>

              <div className="statistical-card-radio">
                <span
                  className={
                    selectedApproach ===
                    "multivariate"
                      ? "radio selected"
                      : "radio"
                  }
                />
              </div>
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="statistical-approach-error">
              {error}
            </div>
          )}

          {/* Continue / preprocessing status */}
          <div className="statistical-approach-actions">
            <button
              type="button"
              className="statistical-continue-button"
              onClick={handleContinue}
              disabled={
                loading ||
                !selectedApproach
              }
              aria-live="polite"
            >
              {loading
                ? "Preprocessing..."
                : "Continue →"}
            </button>
          </div>

          {loading && (
            <div
              role="status"
              aria-live="polite"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginTop: "12px",
                padding: "12px 14px",
                border: "1px solid #cbd5ff",
                borderRadius: "9px",
                background: "#eef2ff",
                color: "#293b8f",
                fontSize: "13px",
                lineHeight: 1.5,
                fontWeight: 600,
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: "15px",
                  height: "15px",
                  flex: "0 0 15px",
                  border: "2px solid #c7d2fe",
                  borderTopColor: "#293b8f",
                  borderRadius: "50%",
                  animation: "statistical-processing-spin 0.8s linear infinite",
                }}
              />
              <span>
                Preprocessing is running in the backend. Please wait while your dataset is being prepared for statistical analysis.
              </span>
            </div>
          )}

          <style>{`
            @keyframes statistical-processing-spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    </div>
  );
}

export default StatisticalApproach;


