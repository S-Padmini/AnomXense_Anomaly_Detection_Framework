# Intelligent Anomaly Insights — Frontend

This frontend implements the Phase 1 → Phase 2 → Phase 3 workflow from the supplied UI specification.

## Run

```powershell
cd C:\Users\padmcons531\Anomaly_Detection\frontend
npm.cmd install
npm.cmd run dev
```

Vite may use `5174` if `5173` is already occupied. Open the URL printed by Vite.

The API defaults to `http://localhost:8000`. To change it, copy `.env.example` to `.env` and set `VITE_API_BASE_URL`.

## Important

Do not run the frontend alone. Start the backend first so upload, column inspection, preprocessing, pagination and statistical analysis are live.
