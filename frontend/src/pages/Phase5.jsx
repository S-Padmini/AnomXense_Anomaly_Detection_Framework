import React, { useEffect, useState } from "react";

import ModelRecommendation from "../components/Phase5/ModelRecommendation";

const API_BASE = `${(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")}/api`;

export default function Phase5({
  datasetId: propDatasetId,
}) {
  const [datasetId, setDatasetId] =
    useState(propDatasetId || null);

  const [data, setData] = useState(null);
  const [loading, setLoading] =
    useState(false);
  const [error, setError] =
    useState("");

  useEffect(() => {
    const savedDatasetId =
      propDatasetId ||
      sessionStorage.getItem("dataset_id") ||
      localStorage.getItem("dataset_id");

    if (savedDatasetId) {
      setDatasetId(savedDatasetId);
    }
  }, [propDatasetId]);

  async function generateRecommendations() {
    if (!datasetId) {
      setError("No dataset has been selected.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE}/phase5/${datasetId}/recommend`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail ||
            "Unable to generate Phase 5 recommendations."
        );
      }

      setData(result);
    } catch (err) {
      setError(
        err.message ||
          "Unable to generate recommendations."
      );
    } finally {
      setLoading(false);
    }
  }

  async function confirmRecommendation() {
    if (!datasetId) {
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/phase5/${datasetId}/confirm`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail ||
            "Unable to confirm Phase 5."
        );
      }

      setData((previous) => ({
        ...previous,
        ...result,
      }));
    } catch (err) {
      setError(
        err.message ||
          "Unable to confirm recommendation."
      );
    }
  }

  useEffect(() => {
    if (datasetId) {
      generateRecommendations();
    }
  }, [datasetId]);

  const recommendations =
    data?.recommendations || [];

  return (
    <div className="phase5-page">
      <div className="phase5-container">

        {/* PAGE HEADER */}
        <div className="phase5-title-section">
          <span className="phase5-phase-label">
            PHASE 05
          </span>

          <h1>
            Model Recommendation
          </h1>

          <p>
            The system evaluates the Phase 3
            statistical evidence together with
            the Phase 4 investigation objective
            to identify the most suitable anomaly
            detection models.
          </p>
        </div>
        
        {/* LOADING */}
        {loading && (
          <div className="phase5-loading">
            <div className="phase5-spinner" />

            <span>
              Analysing dataset and objective...
            </span>
          </div>
        )}

        {/* ERROR */}
        {error && (
          <div className="phase5-error">
            {error}
          </div>
        )}

        {/* TOP 3 RECOMMENDATIONS */}
        {!loading &&
          recommendations.length > 0 && (
            <>
              <div className="phase5-recommendations-section">

                <div className="phase5-section-heading">
                  <div>
                    <h2>
                      🏆 Recommended Models
                    </h2>

                    <span>
                      Top 3 models based on statistical
                      suitability and objective compatibility
                    </span>
                  </div>
                </div>

                <div className="phase5-top-model-list">
                  {recommendations
                    .slice(0, 3)
                    .map((recommendation) => (
                      <ModelRecommendation
                        key={recommendation.model}
                        recommendation={
                          recommendation
                        }
                      />
                    ))}
                </div>
              </div>

              {/* CONFIRM */}
              <div className="phase5-confirm-section">
                <button
                  type="button"
                  className="phase5-confirm-button"
                  onClick={
                    confirmRecommendation
                  }
                >
                  Confirm Recommendation
                </button>
              </div>
            </>
          )}

        {/* EMPTY STATE */}
        {!loading &&
          recommendations.length === 0 &&
          !error && (
            <div className="phase5-empty">
              <h2>
                Model Recommendation
              </h2>

              <p>
                Complete Phase 3 and Phase 4
                before generating the model
                recommendation.
              </p>

              <button
                type="button"
                className="phase5-generate-button"
                onClick={
                  generateRecommendations
                }
              >
                Generate Recommendation
              </button>
            </div>
          )}
      </div>
    </div>
  );
}
