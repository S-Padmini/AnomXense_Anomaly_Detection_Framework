const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  });

  let data = null;
  try { data = await response.json(); } catch { data = null; }

  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed (${response.status})`;
    throw new Error(Array.isArray(message) ? message.map(x => x.msg || String(x)).join(', ') : String(message));
  }
  return data;
}

export const automaticDiscoveryApi = {
  benchmark(datasetId, approach) {
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/benchmark`, {
      method: 'POST',
      body: JSON.stringify({ approach }),
    });
  },

  recommendations(datasetId, scoreMethod = 'combined_score') {
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/recommendations?score_method=${encodeURIComponent(scoreMethod)}`);
  },

  detect(datasetId, { scoreMethod, contaminationMode = 'default', contamination = 0.10, selectedModel }) {
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/detect`, {
      method: 'POST',
      body: JSON.stringify({
        score_method: scoreMethod,
        contamination_mode: contaminationMode,
        contamination: Number(contamination),
        selected_model: selectedModel || null,
      }),
    });
  },

  result(datasetId, { page = 1, pageSize = 50, anomaliesOnly = false } = {}) {
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      anomalies_only: String(anomaliesOnly),
    });
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/result?${query}`);
  },

  columnResult(datasetId, columnName, { page = 1, pageSize = 50, anomaliesOnly = false } = {}) {
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      anomalies_only: String(anomaliesOnly),
    });
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/result/columns/${encodeURIComponent(columnName)}?${query}`);
  },

  anomaly(datasetId, recordNumber, columnName = null) {
    const query = columnName ? `?column_name=${encodeURIComponent(columnName)}` : '';
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/anomaly/${recordNumber}${query}`);
  },

  visualization(datasetId, { columnName = null, limit = 600 } = {}) {
    const query = new URLSearchParams({ limit: String(limit) });
    if (columnName) query.set('column_name', columnName);
    return request(`/api/automatic-discovery/${encodeURIComponent(datasetId)}/visualization?${query}`);
  },
};

export { API_BASE };
