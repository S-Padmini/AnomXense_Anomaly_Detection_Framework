import React from "react";

const approaches = [
  {
    id: "univariate",
    title: "Univariate",
    short: "One feature at a time",
    detail:
      "Each selected feature is examined independently. The automatic models are evaluated separately for each feature.",
    icon: "1D",
  },
  {
    id: "multivariate",
    title: "Multivariate",
    short: "Features jointly",
    detail:
      "All selected features are examined together so the models can detect unusual combinations and relationships.",
    icon: "MD",
  },
];

export default function DetectionApproach({
  value,
  onChange,
  disabled = false,
}) {
  return (
    <section className="ad-card">

      <div className="ad-section-head">

        <div>

          <span className="ad-eyebrow">
            01 · DETECTION APPROACH
          </span>

          <h2>
            How should the data be examined?
          </h2>

          <p>
            Select how Automatic Discovery should
            construct its analysis units.
          </p>

        </div>

        {value && (
          <span className="ad-status-chip">
            Selected:{" "}
            {value === "univariate"
              ? "Univariate"
              : "Multivariate"}
          </span>
        )}

      </div>

      <div className="ad-choice-grid">

        {approaches.map(item => (

          <button
            type="button"
            key={item.id}
            className={`ad-choice ${
              value === item.id
                ? "is-selected"
                : ""
            }`}
            onClick={() =>
              onChange(item.id)
            }
            disabled={disabled}
          >

            <span className="ad-choice-icon">
              {item.icon}
            </span>

            <span className="ad-choice-copy">

              <strong>
                {item.title}
              </strong>

              <span>
                {item.short}
              </span>

              <small>
                {item.detail}
              </small>

            </span>

            <span
              className="ad-radio"
              aria-hidden="true"
            />

          </button>

        ))}

      </div>

    </section>
  );
}