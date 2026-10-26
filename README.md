# WindWise — UK Day-Ahead Wind Forecast Decision Dashboard

**WindWise** is a specialized decision dashboard for UK energy utility day-ahead power buyers. It pairs actual Great Britain national wind generation (**Elexon BMRS FUELHH**) against the latest wind forecasts (**WINDFOR**) that were *actually available at gate close decision time* (default 09:00 UTC on D-1), quantifies empirical forecast errors, and recommends safety buffers to mitigate physical volume shortfall risks.

---

## 1. Project Summary

Power trading teams buy electricity one day before delivery. Because wind generation is intermittent and weather-dependent, buyers must plan safety buffers against forecast errors. WindWise shows the exact forecast available when the buyer had to submit day-ahead bids, evaluates historical accuracy metrics (MAE, RMSE, Bias, P90/P95), and recommends data-driven safety buffers.

- **Target Window:** January 2026 delivery days (30-minute settlement periods).
- **Data Source:** National-level wind only from Elexon BMRS (cached parquet snapshots, zero live external API calls at runtime).
- **Decision Cutoff:** Default 09:00 UTC on D-1 (reflects EPEX SPOT 09:20 auction gate close with a 20-minute operational buffer; fully configurable).

---

## 2. Repository Structure

```
WindWise/
├── PROJECT_PLAN.md           # Multi-phase engineering roadmap and specifications
├── ASSUMPTIONS.md            # Documented market, API, and statistical assumptions
├── DEPLOYMENT.md             # Detailed guide for Docker, Vercel, Render, and Heroku
├── README.md                 # Project documentation and setup guide
├── docker-compose.yml        # Multi-service container orchestration
├── .dockerignore             # Excludes node_modules, .venv, caches from Docker build
├── .gitignore                # Git exclusions
├── .env.example              # Environment variables template
├── render.yaml               # Render cloud deployment blueprint
├── data/
│   ├── actuals.parquet       # Elexon FUELHH wind actuals (Jan 2026, 1,488 periods)
│   └── forecasts.parquet     # Elexon WINDFOR wind forecasts (18,080 rows)
├── backend/
│   ├── Dockerfile            # Python 3.11-slim production container
│   ├── requirements.txt      # Python dependencies (FastAPI, Pandas, PyArrow, etc.)
│   ├── pyproject.toml        # Ruff linter and Pytest configuration
│   ├── Procfile              # Heroku deployment command
│   ├── ingestion/
│   │   └── fetch_data.py     # Elexon API ingest script to build parquet snapshot
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint, CORS, startup data loading
│   │   ├── config.py         # Pydantic Settings (.env configuration)
│   │   ├── schemas.py        # Pydantic response models
│   │   ├── data_store.py     # In-memory parquet cache & vectorised lookup
│   │   ├── core.py           # Pure logic: cutoff selection, errors, metrics, bands
│   │   └── routes.py         # HTTP endpoints (/forecast, /metrics, /decision, etc.)
│   └── tests/
│       ├── test_selection.py # Unit tests for cutoff selection & lead time logic
│       ├── test_metrics.py   # Unit tests for MAE, RMSE, bias, percentiles
│       └── test_api.py       # Integration tests for all 7 API endpoints
└── frontend/
    ├── Dockerfile            # Multi-stage container (Node 20 build -> Nginx Alpine)
    ├── nginx.conf            # Nginx SPA fallback and static caching
    ├── package.json          # React 18, Vite, Recharts, Lucide React
    ├── tsconfig.json         # TypeScript configuration
    ├── vite.config.ts        # Vite configuration
    ├── vercel.json           # Vercel deployment rewrite rules
    ├── index.html            # Main HTML with SEO meta tags & Inter typography
    └── src/
        ├── main.tsx          # React application mount point
        ├── App.tsx           # State management & dashboard assembly
        ├── index.css         # Dark-mode design system & trading terminal styles
        ├── api.ts            # Typed API client
        ├── types.ts          # TypeScript interfaces matching backend models
        └── components/
            ├── Controls.tsx        # Date picker, cutoff time selector, quick jumps
            ├── ForecastChart.tsx   # Chart 1: Actual vs Forecast with P90 band
            ├── KpiCards.tsx        # KPI cards: MAE, RMSE, Bias, P90, Coverage
            ├── DecisionBox.tsx     # Safety buffer recommendation & risk convention
            ├── HorizonChart.tsx    # Chart 2: Accuracy vs Lead Time Horizon
            ├── BreakdownChart.tsx  # Chart 3: Diurnal hour and wind level breakdown
            └── WorstDaysTable.tsx  # Best and worst forecast days ranking table
```

---

## 3. How to Start

### Option A: Using Docker Compose (Recommended)

Make sure Docker Desktop is running, then run from the repository root:

```bash
docker compose up --build
```

- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
- **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

To stop the containers:
```bash
docker compose down
```

---

### Option B: Running Locally Without Docker

#### 1. Backend Setup (Python 3.11+)
```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (Node 18+)
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

### Regenerating the Data Snapshot (Optional)

The repository already comes pre-loaded with verified January 2026 parquet snapshots in `data/`. If you want to re-fetch the raw data directly from the public Elexon Insights API:

```bash
cd backend
python ingestion/fetch_data.py
```
This fetches 7-day chunked streams from Elexon BMRS, validates UTC timestamps, filters for January 2026 target times, removes duplicates, and overwrites `data/actuals.parquet` and `data/forecasts.parquet`.

---

## 4. Live Deployment

- **Live app (Vercel):** https://kjhwr-mocha.vercel.app/
- **Backend API (Render):** https://windwise-backend-x8qp.onrender.com
- **API docs (Swagger):** https://windwise-backend-x8qp.onrender.com/docs

> Note: the backend runs on a free tier and may take about a minute to wake on the first request.

---

## 5. Assumptions and Limitations

1. **Timezone:** All timestamps are timezone-aware **UTC**. In January, the UK is on Greenwich Mean Time (GMT, UTC+0), so UTC equals local UK clock time.
2. **Decision Cutoff:** Default cutoff is set to **09:00 UTC on D-1**.
   - *Reason:* The GB day-ahead EPEX SPOT auction order book closes at 09:20 GMT on D-1. Setting 09:00 provides a 20-minute operational buffer so the buyer only sees forecasts they had before gate close.
   - The cutoff hour and minute are fully configurable in the UI and API.
3. **National Wind Only:** Only national-level Great Britain aggregated wind is included.
4. **Data Coverage:** Elexon FUELHH actuals cover all 1,488 half-hours of January 2026. WINDFOR forecasts are issued on an hourly grid (minute `00`), covering 744 target periods. Missing half-hourly forecasts are explicitly tracked as coverage gaps (50% coverage) rather than artificially filled or interpolated with zero.
5. **Sign Convention:**
   $$\text{Error} = \text{Forecast} - \text{Actual}$$
   - **Positive error ($>0$):** Over-forecast. The forecast predicted more wind than materialized. For an energy buyer, this is the **shortfall risk** direction (the utility under-procures thermal power and faces imbalance cashout charges).
   - **Negative error ($<0$):** Under-forecast. Wind generation exceeded expectations.
6. **Error Uncertainty Sample:** Error percentiles (P50, P90, P95) and the safety buffer recommendation are computed across the full January 2026 dataset (a single-month historical sample).

---

## 6. How to Run Tests & Code Quality Checks

### Pytest (Unit & Integration Tests)
The test suite consists of 26 tests covering cutoff selection, vectorised pairings, metric calculations (hand-verified), and FastAPI endpoint schemas:

```bash
cd backend
pytest -v
```

### Ruff (Linting & Code Formatting)
```bash
cd backend
ruff check app tests
ruff format --check app tests
```

### Frontend Type Check & Production Build
```bash
cd frontend
npm run build
```

---

## 7. AI Tools Disclosure

As required by the client specification, the following AI tools and models were used during the development of this project:

- **AI Assistant:** Google DeepMind Advanced Agentic Coding Assistant (Antigravity IDE).
- **Underlying Model:** Gemini 3.8 Flash.
- **Specific Tasks Assisted by AI:**
  1. *Architecture & Planning:* Generating the phase-by-phase implementation plan ([PROJECT_PLAN.md](PROJECT_PLAN.md)) and documenting domain assumptions ([ASSUMPTIONS.md](ASSUMPTIONS.md)).
  2. *Data Ingestion:* Researching and verifying Elexon BMRS OpenAPI stream specifications (`FUELHH/stream` and `WINDFOR/stream`).
  3. *Core Algorithm:* Implementing the vectorised latest-forecast-before-cutoff selection logic and hand-calculating verification tests in [core.py](backend/app/core.py).
  4. *API Engineering:* Building typed FastAPI routers, Pydantic schemas, in-memory parquet caching, and CORS configuration.
  5. *Frontend Interface:* Crafting the dark-mode React + TypeScript + Recharts dashboard components ([ForecastChart](frontend/src/components/ForecastChart.tsx), [KpiCards](frontend/src/components/KpiCards.tsx), [DecisionBox](frontend/src/components/DecisionBox.tsx), [HorizonChart](frontend/src/components/HorizonChart.tsx), [BreakdownChart](frontend/src/components/BreakdownChart.tsx), [WorstDaysTable](frontend/src/components/WorstDaysTable.tsx)).
  6. *Docker & DevOps:* Creating multi-stage Dockerfiles, Docker Compose orchestrations, and deployment descriptors.
