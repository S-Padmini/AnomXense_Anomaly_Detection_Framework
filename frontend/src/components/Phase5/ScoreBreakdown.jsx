import React, { useState } from "react";

import StatisticalScore from "./StatisticalScore";
import ObjectiveScore from "./ObjectiveScore";

export default function ScoreBreakdown({
  recommendation,
}) {
  const [showStatistical, setShowStatistical] =
    useState(false);

  const [showObjective, setShowObjective] =
    useState(false);

  if (!recommendation) {
    return null;
  }

  const statisticalScore =
    Number(
      recommendation.statistical_score || 0
    ).toFixed(1);

  const objectiveScore =
    Number(
      recommendation.objective_score || 0
    ).toFixed(1);

  const finalScore =
    Number(
      recommendation.final_score || 0
    ).toFixed(1);

  return (
    <div className="phase5-score-breakdown">

      {/* SCORE SUMMARY */}
      <div className="phase5-score-summary">

        <div className="phase5-score-summary-item">
          <span>
            Statistical Suitability
          </span>

          <strong>
            {statisticalScore}
            <small>/70</small>
          </strong>
        </div>

        <div className="phase5-score-summary-item">
          <span>
            Objective Compatibility
          </span>

          <strong>
            {objectiveScore}
            <small>/30</small>
          </strong>
        </div>

        <div className="phase5-score-summary-item phase5-score-final">
          <span>
            Final Score
          </span>

          <strong>
            {finalScore}
            <small>/100</small>
          </strong>
        </div>

      </div>

      {/* STATISTICAL DROPDOWN */}
      <button
        type="button"
        className="phase5-dropdown-button"
        onClick={() =>
          setShowStatistical(
            !showStatistical
          )
        }
      >
        <span>
          Statistical Suitability
        </span>

        <span>
          {statisticalScore}/70
        </span>

        <span className="phase5-dropdown-arrow">
          {showStatistical
            ? "▲"
            : "▼"}
        </span>
      </button>

      {showStatistical && (
        <StatisticalScore
          details={
            recommendation.statistical_details ||
            []
          }
        />
      )}

      {/* OBJECTIVE DROPDOWN */}
      <button
        type="button"
        className="phase5-dropdown-button"
        onClick={() =>
          setShowObjective(
            !showObjective
          )
        }
      >
        <span>
          Objective Compatibility
        </span>

        <span>
          {objectiveScore}/30
        </span>

        <span className="phase5-dropdown-arrow">
          {showObjective
            ? "▲"
            : "▼"}
        </span>
      </button>

      {showObjective && (
        <ObjectiveScore
          details={
            recommendation.objective_details ||
            []
          }
        />
      )}

    </div>
  );
}