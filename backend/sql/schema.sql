CREATE TABLE IF NOT EXISTS ground_stations (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) UNIQUE NOT NULL,
  lat DOUBLE PRECISION NOT NULL,
  lon DOUBLE PRECISION NOT NULL,
  elevation_m DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS satellites (
  id SERIAL PRIMARY KEY,
  norad_id INTEGER UNIQUE NOT NULL,
  name VARCHAR(160) NOT NULL,
  tle_line1 VARCHAR(80) NOT NULL,
  tle_line2 VARCHAR(80) NOT NULL,
  mission_priority INTEGER NOT NULL DEFAULT 5 CHECK (mission_priority BETWEEN 1 AND 10),
  satellite_type VARCHAR(32) NOT NULL DEFAULT 'commercial',
  tle_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS passes (
  id SERIAL PRIMARY KEY,
  satellite_id INTEGER NOT NULL REFERENCES satellites(id) ON DELETE CASCADE,
  ground_station_id INTEGER NOT NULL REFERENCES ground_stations(id) ON DELETE CASCADE,
  aos_time TIMESTAMPTZ NOT NULL,
  los_time TIMESTAMPTZ NOT NULL,
  max_elevation_deg DOUBLE PRECISION NOT NULL,
  duration_seconds INTEGER NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'scheduled'
);

CREATE TABLE IF NOT EXISTS conflicts (
  id SERIAL PRIMARY KEY,
  pass_id_winner INTEGER NOT NULL REFERENCES passes(id) ON DELETE CASCADE,
  pass_id_loser INTEGER NOT NULL REFERENCES passes(id) ON DELETE CASCADE,
  conflict_reason TEXT NOT NULL,
  resolution_reason TEXT NOT NULL,
  alternative_window TEXT,
  resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS schedules (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  ground_station_id INTEGER NOT NULL REFERENCES ground_stations(id) ON DELETE CASCADE,
  pass_id INTEGER NOT NULL REFERENCES passes(id) ON DELETE CASCADE,
  slot_order INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_schedule_day_station_pass UNIQUE (date, ground_station_id, pass_id)
);

CREATE INDEX IF NOT EXISTS ix_passes_aos_time ON passes (aos_time);
CREATE INDEX IF NOT EXISTS ix_passes_satellite_id ON passes (satellite_id);
CREATE INDEX IF NOT EXISTS ix_passes_ground_station_id ON passes (ground_station_id);
CREATE INDEX IF NOT EXISTS ix_passes_status ON passes (status);

CREATE OR REPLACE VIEW daily_schedule_view AS
SELECT
  sc.id AS schedule_id,
  sc.date,
  sc.slot_order,
  gs.id AS ground_station_id,
  gs.name AS ground_station_name,
  gs.lat,
  gs.lon,
  sat.id AS satellite_id,
  sat.norad_id,
  sat.name AS satellite_name,
  sat.mission_priority,
  sat.satellite_type,
  p.id AS pass_id,
  p.aos_time,
  p.los_time,
  p.max_elevation_deg,
  p.duration_seconds,
  p.status
FROM schedules sc
JOIN passes p ON p.id = sc.pass_id
JOIN satellites sat ON sat.id = p.satellite_id
JOIN ground_stations gs ON gs.id = sc.ground_station_id;
