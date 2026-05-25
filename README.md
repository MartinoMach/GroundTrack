# GroundTrack

<p align="center">
  <img src="./docs/groundtrack-logo.svg" alt="GroundTrack logo" width="760">
</p>

GroundTrack is a full-stack ground station pass planning and conflict simulator for satellite operations. It pulls live CelesTrak TLEs, computes upcoming visibility windows with Skyfield, detects overlapping contacts, chooses the strongest contact plan by mission value, and presents the result in an Angular operator dashboard.

Think of it as a compact mission-planning console: orbital data comes in, pass windows are generated, collisions in the antenna schedule are explained, and the operator gets a clear daily plan instead of a pile of raw ephemeris math.

## Project Scope

GroundTrack models the core workflow of a small satellite operations desk:

- Ingest public TLE data for the ISS, the first 50 Starlink satellites, NOAA 15/18/19, and amateur spacecraft.
- Maintain a PostgreSQL catalog of satellites, ground stations, pass windows, schedule slots, and conflict reports.
- Compute the next 24 hours of satellite visibility for configurable ground stations.
- Score each contact opportunity using mission priority, maximum elevation, pass duration, and satellite type.
- Resolve overlapping antenna windows with a greedy interval scheduling strategy.
- Generate human-readable conflict reasons, resolution reasons, and possible alternate windows.
- Support historical replay through the same simulation surface used for live recomputation.
- Expose a dashboard with a pass timeline, conflict review panel, live station map, and satellite position dots.

## Why It Exists

Ground stations are scarce resources. A single antenna cannot service every spacecraft visible above the horizon at the same time, and the best pass is not always the first pass. GroundTrack turns that tradeoff into an inspectable scheduling problem:

- operators can see which contacts are available,
- mission leads can tune satellite priority,
- conflicts are preserved as explainable records,
- dashboards can compare the greedy resolver against a pairwise brute-force baseline estimate,
- future scheduling experiments can plug into a real API and schema instead of starting from scratch.

## System Architecture

```text
CelesTrak TLE feeds
        |
        v
TLE ingestion service
        |
        v
PostgreSQL satellite + station catalog
        |
        v
Skyfield pass computation
        |
        v
Priority conflict resolver
        |
        v
Schedule view + conflict reports
        |
        v
FastAPI JSON API
        |
        v
Angular operator dashboard
```

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.x, APScheduler, Skyfield
- PostgreSQL 15+
- TypeScript, Angular 17+, Leaflet
- No Docker configuration

## Core Modules

- `backend/app/services/tle_ingestion.py` ingests CelesTrak data for configured satellite groups.
- `backend/app/services/pass_computation.py` computes 24-hour visibility windows and current positions.
- `backend/app/services/conflict_resolver.py` ranks overlapping passes and writes schedule/conflict records.
- `backend/app/services/simulation.py` powers historical replay through `POST /api/replay`.
- `backend/app/services/pipeline.py` orchestrates TLE refresh, pass computation, and conflict resolution.
- `backend/app/api/routes.py` exposes the FastAPI routes used by the dashboard.
- `backend/sql/schema.sql` defines tables, indexes, enums, and `daily_schedule_view`.
- `frontend/src/app/pass-timeline` renders the Gantt-style contact timeline.
- `frontend/src/app/conflict-dashboard` presents conflict reports and re-resolution controls.
- `frontend/src/app/station-map` displays stations and current satellite position dots with Leaflet.

## Scheduling Model

Every pass starts as a candidate contact window with acquisition of signal, loss of signal, max elevation, duration, satellite type, and mission priority. The resolver groups passes by ground station and date, then chooses a non-overlapping schedule.

The scoring blend is:

- mission priority as the dominant operator-controlled value,
- maximum elevation as a quality-of-contact signal,
- pass duration as the available communication window,
- satellite type weight to bias critical mission classes.

Losing contacts are not discarded silently. GroundTrack marks them as deprioritized, stores the winner/loser relationship, explains the scoring decision, and searches for the next available alternate window for the same satellite and station.

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

The scheduler runs automatically every hour by default.

## Backend Configuration

- `DATABASE_URL` sets the PostgreSQL connection string.
- `TLE_REFRESH_HOURS` defaults to `24`.
- `RECOMPUTE_INTERVAL_MINUTES` defaults to `60`.
- `SCHEDULER_ENABLED` defaults to `true`.
- `CORS_ORIGINS` defaults to `["http://localhost:4200"]`.

## API Surface

- `GET /api/passes?satellite_id=&ground_station_id=&min_elevation=` lists upcoming pass windows.
- `GET /api/schedule/daily` returns the current daily schedule view.
- `GET /api/conflicts` returns detected and resolved contact conflicts.
- `POST /api/conflicts/{conflict_id}/resolve` reruns daily conflict resolution.
- `POST /api/groundstations` creates a station.
- `GET /api/groundstations` lists stations.
- `GET /api/satellites` lists tracked satellites and TLE age.
- `PUT /api/satellites/{satellite_id}/priority` updates mission priority.
- `POST /api/replay` runs live recompute, or accepts `{ "date": "YYYY-MM-DD", "ground_station_id": 1 }` for replay.
- `GET /api/stats` returns dashboard metrics.
- `GET /api/positions` returns current satellite positions.

## Frontend Setup

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`.

## Default Scenario

Pipeline runs create three default stations:

- Wallops Island
- Svalbard
- Yatharagga

Those stations give the dashboard immediate operational variety: coastal U.S. passes, high-latitude coverage, and southern-hemisphere contacts.

## Future Expansion

GroundTrack is intentionally shaped so more advanced scheduling ideas can be added without replacing the whole system:

- station maintenance windows and blackout periods,
- antenna capabilities and frequency-band constraints,
- downlink volume estimates,
- operator authentication and audit trails,
- multi-day planning horizons,
- pluggable optimization strategies,
- exports for mission planning reports.
