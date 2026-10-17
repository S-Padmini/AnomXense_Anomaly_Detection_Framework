import React from "react";

export default function StatisticalScore({
  details = [],
}) {
  return (
    <div className="phase5-score-list">

      {details.map((item, index) => {
        const name =
          item.name ||
          item.factor ||
          `Characteristic ${index + 1}`;

        const score =
          Number(
            item.score || 0
          ).toFixed(1);

        return (
          <div
            className="phase5-score-list-row"
            key={`${name}-${index}`}
          >
            <span>
              {name}
            </span>

            <strong>
              {score}/7
            </strong>
          </div>
        );
      })}

    </div>
  );
}