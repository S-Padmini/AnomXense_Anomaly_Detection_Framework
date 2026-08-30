# Intelligent Anomaly Insights — Backend

FastAPI backend for the dynamic Phase 1 → Phase 3 workflow.

## Run

```powershell
cd C:\Users\padmcons531\Anomaly_Detection\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

API documentation: `http://localhost:8000/docs`

Health check: `http://localhost:8000/health`

## Tests

```powershell
python -m pytest -q
```

The test suite checks:
- 9 Phase-1 summary metrics and dynamic column classification
- customer_name is categorical rather than an identifier
- Phase-2 selection/confirmation
- Phase-3 missing/duplicate inspection
- preprocessing counts and before/after rows
- 10 statistical-analysis sections
- duplicate detection occurs before imputation

## Supported upload formats

CSV, TSV/TAB, JSON, XLSX and XLS (subject to the installed pandas/openpyxl support).

The dataset store is intentionally in-memory for local development. A production multi-worker deployment should move session state to shared storage.
