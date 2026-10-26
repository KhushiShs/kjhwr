# Deployment Guide & Environment Variables

This document details deployment options for the **WindWise** UK Day-Ahead Wind Forecast Decision Dashboard.

---

## 1. Docker Compose (Local & Self-Hosted Production)

The entire application can be run locally or on any cloud VM using Docker Compose.

### Quick Start
```bash
docker compose up --build
```

### Services & Port Mappings
- **Frontend (Nginx + React SPA)**: `http://localhost:5173` (internal port 80)
- **Backend (FastAPI + Uvicorn)**: `http://localhost:8000` (internal port 8000)

### Environment Variables
| Variable | Service | Default | Description |
|---|---|---|---|
| `PORT` | backend | `8000` | Port uvicorn binds to |
| `HOST` | backend | `0.0.0.0` | Network interface |
| `CORS_ORIGINS` | backend | `http://localhost:5173,http://localhost:3000` | Comma-separated list of allowed origins or `*` |
| `DATA_DIR` | backend | `/app/data` | Path to directory containing cached `actuals.parquet` and `forecasts.parquet` |
| `DEFAULT_CUTOFF_HOUR` | backend | `9` | Default decision cutoff hour (UTC) on D-1 |
| `DEFAULT_CUTOFF_MINUTE` | backend | `0` | Default decision cutoff minute (UTC) on D-1 |
| `VITE_API_URL` | frontend (build arg) | `http://localhost:8000` | Base URL of backend API |

---

## 2. Cloud Deployment: Frontend on Vercel

The frontend is a Vite + React SPA ready for zero-config Vercel deployment.

1. Connect the repository to [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Framework Preset: **Vite** (auto-detected).
4. In **Environment Variables**, add:
   ```
   VITE_API_URL=https://<your-backend-domain>.onrender.com
   ```
5. Deploy. Routing is automatically handled by `frontend/vercel.json`.

---

## 3. Cloud Deployment: Backend on Render or Heroku

### Option A: Render (Web Service / Docker)
A blueprint specification is provided in `render.yaml`.
1. Connect repo to [Render](https://render.com).
2. Create a **Web Service** using Docker.
3. Settings:
   - **Docker Context**: `.` (repository root)
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Health Check Path**: `/health`
4. Set Environment Variables:
   ```
   CORS_ORIGINS=https://<your-vercel-app>.vercel.app
   DATA_DIR=/app/data
   ```

### Option B: Heroku (Container Registry or Python Buildpack)
A `backend/Procfile` is provided:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
1. Create Heroku app: `heroku create windwise-backend`
2. Set configuration:
   ```bash
   heroku config:set CORS_ORIGINS="https://<your-vercel-app>.vercel.app"
   ```
3. Deploy container:
   ```bash
   heroku container:push web -a windwise-backend
   heroku container:release web -a windwise-backend
   ```
