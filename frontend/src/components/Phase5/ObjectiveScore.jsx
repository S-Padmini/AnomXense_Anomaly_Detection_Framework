import React from "react";

export default function ObjectiveScore({
  details = [],
}) {
  return (
    <div className="phase5-score-list">

      {details.map((item, index) => {
        const name =
          item.name ||
          item.factor ||
          `Objective Component ${index + 1}`;

        const score =
          Number(
            item.score || 0
          ).toFixed(1);

        let maximum =
          item.maximum ??
          item.max_score;

        if (maximum === undefined) {
          if (index === 0) {
            maximum = 15;
          } else if (index === 1) {
            maximum = 10;
          } else {
            maximum = 5;
          }
        }

        return (
          <div
            className="phase5-score-list-row"
            key={`${name}-${index}`}
          >
            <span>
              {name}
            </span>

            <strong>
              {score}/{Number(
                maximum
              ).toFixed(0)}
            </strong>
          </div>
        );
      })}

    </div>
  );
}