import React, { useState } from "react";
import ScoreBreakdown from "./ScoreBreakdown";

export default function ModelRecommendation({
  recommendation,
}) {
  const [expanded, setExpanded] =
    useState(false);

  if (!recommendation) {
    return null;
  }

  const displayName =
    recommendation.display_name ||
    recommendation.model;

  const score = Number(
    recommendation.final_score || 0
  ).toFixed(1);

  return (
    <div className="phase5-model-card">

      {/* MODEL HEADER */}
      <div className="phase5-model-card-header">

        <div className="phase5-model-rank-badge">
          #{recommendation.rank}
        </div>

        <div className="phase5-model-main-info">
          <div className="phase5-model-label">
            {recommendation.rank === 1
              ? "TOP RECOMMENDATION"
              : "RECOMMENDED MODEL"}
          </div>

          <h3>
            {displayName}
          </h3>

          {recommendation.category && (
            <span className="phase5-model-category">
              {recommendation.category}
            </span>
          )}
        </div>

        <div className="phase5-model-final-score">
          <strong>
            {score}
          </strong>

          <span>
            /100
          </span>
        </div>
      </div>

      {/* DESCRIPTION */}
      {recommendation.description && (
        <p className="phase5-model-description">
          {recommendation.description}
        </p>
      )}

      {/* VIEW SCORE */}
      <button
        type="button"
        className="phase5-score-button"
        onClick={() =>
          setExpanded(!expanded)
        }
      >
        <span>
          {expanded
            ? "Hide Score"
            : "View Score"}
        </span>

        <span className="phase5-score-arrow">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* SCORE BREAKDOWN */}
      {expanded && (
        <ScoreBreakdown
          recommendation={
            recommendation
          }
        />
      )}
    </div>
  );
}