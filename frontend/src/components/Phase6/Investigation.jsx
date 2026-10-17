import { useMemo } from "react";

function score(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(6) : "—";
}

function getStatus(record) {
  const value = String(
    record?.status ??
    record?.anomaly_status ??
    ""
  ).trim().toLowerCase();

  if (
    value === "anomaly" ||
    value === "outlier" ||
    value.includes("anomal")
  ) {
    return "Anomaly";
  }

  if (value === "normal" || value === "inlier") {
    return "Normal";
  }

  if (typeof record?.is_anomaly === "boolean") {
    return record.is_anomaly ? "Anomaly" : "Normal";
  }

  return "Normal";
}

function recordId(record) {
  return String(
    record?.record_id ??
    record?.customer_id ??
    record?.id ??
    record?.record_index ??
    "—"
  );
}

export default function Investigation({
  records = [],
  result,
  search = "",
  onSearch,
  sort = "score",
  onSort,
  onSelect,
}) {
  const columns = useMemo(() => {
    const preferred = [
      ...(result?.target_columns || []),
      ...(result?.explain_by_columns || []),
    ];

    return [...new Set(preferred)]
      .filter((column) => column !== "anomaly_score");
  }, [result]);

  return (
    <section className="p6-panel p6-investigation-panel">
      <div className="p6-table-head">
        <div>
          <div className="p6-eyebrow">02 · INVESTIGATION</div>
          <h3>Detected Anomalies</h3>
          <p className="p6-table-subtitle">
            Select a detected record to open its score, feature evidence and contextual explanation.
          </p>
        </div>

        <div className="p6-table-controls">
          <div className="p6-table-search-wrap">
            <span aria-hidden="true">⌕</span>
            <input
              className="p6-table-search"
              placeholder="Search records..."
              value={search}
              onChange={(event) => onSearch(event.target.value)}
              aria-label="Search detected anomaly records"
            />
          </div>

          <select
            value={sort}
            onChange={(event) => onSort?.(event.target.value)}
            aria-label="Sort detected anomalies"
          >
            <option value="score">Highest score</option>
            <option value="rank">Detection rank</option>
            <option value="record">Record index</option>
          </select>
        </div>
      </div>

      <div className="p6-table-meta">
        <span>{records.length} anomaly records shown</span>
        <span>Click a row to investigate</span>
      </div>

      <div className="p6-table-wrap">
        <table className="p6-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Record</th>
              <th>Anomaly Score</th>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {records.map((row, index) => {
              const rowStatus = getStatus(row);

              return (
                <tr
                  key={`${row?.record_index ?? recordId(row)}-${row?.rank ?? index}`}
                  className={rowStatus === "Anomaly" ? "p6-anomaly-row" : ""}
                  onClick={() => onSelect?.(row)}
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect?.(row);
                    }
                  }}
                >
                  <td>{row?.rank ?? index + 1}</td>
                  <td>
                    <strong className="p6-record-id">{recordId(row)}</strong>
                  </td>
                  <td className="score-cell">{score(row?.anomaly_score)}</td>

                  {columns.map((column) => (
                    <td key={column}>
                      {String(row?.[column] ?? "—")}
                    </td>
                  ))}

                  <td>
                    <span className={`p6-status ${rowStatus.toLowerCase()}`}>
                      <i aria-hidden="true" />
                      {rowStatus}
                    </span>
                  </td>
                </tr>
              );
            })}

            {!records.length && (
              <tr>
                <td colSpan={columns.length + 4} className="p6-empty-cell">
                  No anomaly records match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="p6-table-hint">
        Click any record to inspect its score, target-feature evidence, selected Explain By context, and business explanation.
      </p>
    </section>
  );
}

export function FilterPanel({
  schema = [],
  records = [],
  filters = {},
  onChange,
  onReset,
}) {
  function setFilter(column, value) {
    onChange({
      ...filters,
      [column]: value,
    });
  }

  function clearColumn(column) {
    const next = { ...filters };
    delete next[column];
    onChange(next);
  }

  return (
    <div className="p6-filter-panel p6-royal-filter-panel">
      <div className="p6-filter-head">
        <div>
          <strong>FILTER RECORDS</strong>
          <span>
            Every selected Target and Explain By column is available for investigation.
          </span>
        </div>
        <button
          type="button"
          className="p6-reset-button"
          onClick={onReset}
        >
          Reset Filters
        </button>
      </div>

      <div className="p6-filter-grid">
        {schema.map((item) => {
          const column = item?.column;
          if (!column) return null;

          const type = item?.type || "text";
          const value = filters?.[column];

          if (type === "numeric") {
            return (
              <div className="p6-filter-card" key={column}>
                <label>{column}</label>
                <div className="p6-filter-range">
                  <input
                    type="number"
                    placeholder={`Min ${item?.min ?? ""}`}
                    value={value?.min ?? ""}
                    onChange={(event) =>
                      setFilter(column, {
                        ...(value || {}),
                        min: event.target.value,
                      })
                    }
                  />
                  <input
                    type="number"
                    placeholder={`Max ${item?.max ?? ""}`}
                    value={value?.max ?? ""}
                    onChange={(event) =>
                      setFilter(column, {
                        ...(value || {}),
                        max: event.target.value,
                      })
                    }
                  />
                </div>
                {value && (value.min !== "" || value.max !== "") && (
                  <button type="button" className="p6-filter-clear" onClick={() => clearColumn(column)}>
                    Clear
                  </button>
                )}
              </div>
            );
          }

          if (type === "categorical" || type === "boolean") {
            const options = Array.isArray(item?.values) ? item.values : [];
            return (
              <div className="p6-filter-card" key={column}>
                <label>{column}</label>
                <select
                  value={Array.isArray(value) && value.length ? value[0] : ""}
                  onChange={(event) =>
                    setFilter(column, event.target.value ? [event.target.value] : [])
                  }
                >
                  <option value="">All values</option>
                  {options.map((option) => (
                    <option key={String(option)} value={String(option)}>
                      {String(option)}
                    </option>
                  ))}
                </select>
                {value?.length ? (
                  <button type="button" className="p6-filter-clear" onClick={() => clearColumn(column)}>
                    Clear
                  </button>
                ) : null}
              </div>
            );
          }

          return (
            <div className="p6-filter-card" key={column}>
              <label>{column}</label>
              <input
                type="text"
                placeholder={`Search ${column}`}
                value={typeof value === "string" ? value : ""}
                onChange={(event) => setFilter(column, event.target.value)}
              />
              {value ? (
                <button type="button" className="p6-filter-clear" onClick={() => clearColumn(column)}>
                  Clear
                </button>
              ) : null}
            </div>
          );
        })}
      </div>

      {!schema.length && (
        <div className="p6-honest-empty">
          No Target or Explain By columns are available for filtering.
        </div>
      )}
    </div>
  );
}
