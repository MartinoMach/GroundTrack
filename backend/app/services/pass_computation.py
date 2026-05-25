from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from skyfield.api import EarthSatellite, load, wgs84

from app.models import GroundStation, PassStatus, PassWindow, Satellite

logger = logging.getLogger(__name__)


DEFAULT_STATIONS = [
    {"name": "Wallops Island", "lat": 37.9402, "lon": -75.4664, "elevation_m": 3},
    {"name": "Svalbard", "lat": 78.2298, "lon": 15.4078, "elevation_m": 458},
    {"name": "Yatharagga", "lat": -29.0464, "lon": 115.3467, "elevation_m": 250},
]


class PassComputationEngine:
    """Skyfield-based pass engine; all orbital mechanics are delegated to Skyfield TLE propagation."""

    def __init__(self, db: Session):
        self.db = db
        self.timescale = load.timescale()

    def ensure_default_ground_stations(self) -> None:
        for station_data in DEFAULT_STATIONS:
            exists = self.db.scalar(select(GroundStation).where(GroundStation.name == station_data["name"]))
            if exists is None:
                self.db.add(GroundStation(**station_data))
        self.db.commit()

    def compute_next_24h(self, start: datetime | None = None, ground_station_id: int | None = None) -> dict:
        started = time.perf_counter()
        start = start or datetime.now(UTC)
        end = start + timedelta(hours=24)
        station_query = select(GroundStation)
        if ground_station_id:
            station_query = station_query.where(GroundStation.id == ground_station_id)
        stations = list(self.db.scalars(station_query))
        satellites = list(self.db.scalars(select(Satellite)))

        # The rolling operational horizon is rebuilt each run to avoid stale pass rows from old TLEs.
        delete_query = delete(PassWindow).where(PassWindow.aos_time >= start, PassWindow.aos_time < end)
        if ground_station_id:
            delete_query = delete_query.where(PassWindow.ground_station_id == ground_station_id)
        self.db.execute(delete_query)

        generated = 0
        for station in stations:
            observer = wgs84.latlon(station.lat, station.lon, elevation_m=station.elevation_m)
            t0 = self.timescale.from_datetime(start)
            t1 = self.timescale.from_datetime(end)
            for sat in satellites:
                sky_sat = EarthSatellite(sat.tle_line1, sat.tle_line2, sat.name, self.timescale)
                times, events = sky_sat.find_events(observer, t0, t1, altitude_degrees=5.0)
                generated += self._persist_pass_events(sat, station, sky_sat, observer, times, events)

        self.db.commit()
        elapsed = time.perf_counter() - started
        logger.info("Pass computation completed in %.2fs; generated %s passes", elapsed, generated)
        return {"passes_generated": generated, "seconds": elapsed}

    def _persist_pass_events(self, sat: Satellite, station: GroundStation, sky_sat, observer, times, events) -> int:
        count = 0
        rise = culminate = None
        for t, event in zip(times, events, strict=False):
            if event == 0:
                rise = t
            elif event == 1:
                culminate = t
            elif event == 2 and rise is not None:
                aos = rise.utc_datetime().replace(tzinfo=UTC)
                los = t.utc_datetime().replace(tzinfo=UTC)
                max_elevation = self._max_elevation_deg(sky_sat, observer, rise, culminate or t, t)
                self.db.add(
                    PassWindow(
                        satellite_id=sat.id,
                        ground_station_id=station.id,
                        aos_time=aos,
                        los_time=los,
                        max_elevation_deg=max_elevation,
                        duration_seconds=max(0, int((los - aos).total_seconds())),
                        status=PassStatus.SCHEDULED,
                    )
                )
                count += 1
                rise = culminate = None
        return count

    def _max_elevation_deg(self, sky_sat, observer, rise, culminate, set_time) -> float:
        sample_times = [rise, culminate, set_time]
        elevations = []
        for sample in sample_times:
            difference = sky_sat - observer
            topocentric = difference.at(sample)
            alt, _, _ = topocentric.altaz()
            elevations.append(alt.degrees)
        return round(max(elevations), 2)

    def current_positions(self) -> list[dict]:
        now = self.timescale.now()
        positions: list[dict] = []
        for sat in self.db.scalars(select(Satellite)):
            sky_sat = EarthSatellite(sat.tle_line1, sat.tle_line2, sat.name, self.timescale)
            subpoint = wgs84.subpoint(sky_sat.at(now))
            positions.append({"satellite_id": sat.id, "name": sat.name, "lat": subpoint.latitude.degrees, "lon": subpoint.longitude.degrees})
        return positions
