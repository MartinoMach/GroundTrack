# GroundTrack

GroundTrack is a full-stack ground station pass planning and conflict simulator. It ingests real CelesTrak TLEs, computes spacecraft pass windows with Skyfield, resolves overlapping visibility windows by mission priority, and exposes an Angular operator dashboard.

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.x, APScheduler, Skyfield
- PostgreSQL 15+
- TypeScript, Angular 17+, Leaflet
- No Docker configuration

## Project Layout

- `backend/app/services/tle_ingestion.py` - CelesTrak ingestion for ISS, first 50 Starlink satellites, NOAA 15/18/19, and amateur satellites.
- `backend/app/services/pass_computation.py` - Skyfield pass computation for configurable ground stations over the next 24 hours.
- `backend/app/services/conflict_resolver.py` - priority-based overlap detection, conflict reports, and schedule generation.
- `backend/app/services/simulation.py` - historical replay pipeline for `POST /api/replay`.
- `backend/app/api/routes.py` - FastAPI routes and service orchestration.
- `backend/sql/schema.sql` - PostgreSQL tables, indexes, and `daily_schedule_view`.
- `frontend/src/app/pass-timeline` - Gantt-style pass timeline.
- `frontend/src/app/conflict-dashboard` - conflict reports and re-resolution controls.
- `frontend/src/app/station-map` - Leaflet station map and satellite position dots.

## Backend Setup

Create a PostgreSQL database:

```bash
createdb groundtrack
psql groundtrack -f backend/sql/schema.sql
```

Create a virtual environment and install dependencies:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the API:

```bash
DATABASE_URL="postgresql+psycopg://groundtrack:groundtrack@localhost:5432/groundtrack" \
uvicorn app.main:app --reload
```

Trigger the first live recompute:

```bash
curl -X POST http://localhost:8000/api/replay
```

The scheduler also runs automatically every hour by default. Configure it with:

- `DATABASE_URL`
- `TLE_REFRESH_HOURS` default `24`
- `RECOMPUTE_INTERVAL_MINUTES` default `60`
- `SCHEDULER_ENABLED` default `true`
- `CORS_ORIGINS` default `["http://localhost:4200"]`

## API

- `GET /api/passes?satellite_id=&ground_station_id=&min_elevation=`
- `GET /api/schedule/daily`
- `GET /api/conflicts`
- `POST /api/groundstations`
- `GET /api/groundstations`
- `GET /api/satellites`
- `PUT /api/satellites/{satellite_id}/priority`
- `POST /api/replay` with optional `{ "date": "YYYY-MM-DD", "ground_station_id": 1 }`
- `GET /api/stats`
- `GET /api/positions`

## Frontend Setup

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`.

## Notes

The backend creates three default stations on pipeline runs: Wallops Island, Svalbard, and Yatharagga. The conflict resolver uses a greedy interval scheduling pass scored by mission priority, maximum elevation, duration, and satellite type weight. It also reports a pairwise brute-force baseline estimate so demos can show the speedup target against an `O(n^2)` approach.
