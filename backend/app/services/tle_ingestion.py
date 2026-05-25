from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Satellite, SatelliteType

logger = logging.getLogger(__name__)


class TleIngestionService:
    """Fetches real CelesTrak TLEs and stores the latest orbital state in PostgreSQL."""

    CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php"
    GROUPS = {
        "stations": SatelliteType.SCIENCE,
        "starlink": SatelliteType.COMMERCIAL,
        "noaa": SatelliteType.WEATHER,
        "amateur": SatelliteType.AMATEUR,
    }

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    async def refresh_if_stale(self) -> int:
        newest = self.db.scalar(select(Satellite.tle_fetched_at).order_by(Satellite.tle_fetched_at.desc()).limit(1))
        if newest and newest > datetime.now(UTC) - timedelta(hours=self.settings.tle_refresh_hours):
            logger.info("TLE cache is fresh; skipping CelesTrak fetch")
            return 0
        return await self.refresh_all()

    async def refresh_all(self) -> int:
        updated = 0
        async with httpx.AsyncClient(timeout=30) as client:
            for group, sat_type in self.GROUPS.items():
                params = {"GROUP": group, "FORMAT": "TLE"}
                response = await client.get(self.CELESTRAK, params=params)
                response.raise_for_status()
                records = self._parse_tle_text(response.text, sat_type)
                if group == "stations":
                    records = [record for record in records if record["name"].upper().startswith("ISS")]
                if group == "starlink":
                    records = records[:50]
                if group == "noaa":
                    wanted = {"NOAA 15", "NOAA 18", "NOAA 19"}
                    records = [record for record in records if record["name"].upper() in wanted]

                for record in records:
                    self._upsert_satellite(record)
                    updated += 1
        self.db.commit()
        logger.info("Fetched %s CelesTrak TLE records", updated)
        return updated

    def _parse_tle_text(self, text: str, sat_type: SatelliteType) -> list[dict]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        records: list[dict] = []
        for i in range(0, len(lines) - 2, 3):
            name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
            if not line1.startswith("1 ") or not line2.startswith("2 "):
                continue
            norad_id = int(line1[2:7])
            records.append(
                {
                    "norad_id": norad_id,
                    "name": name,
                    "tle_line1": line1,
                    "tle_line2": line2,
                    "satellite_type": sat_type.value,
                    "mission_priority": self._default_priority(sat_type, name),
                }
            )
        return records

    def _default_priority(self, sat_type: SatelliteType, name: str) -> int:
        if name.upper().startswith("ISS"):
            return 10
        return {
            SatelliteType.WEATHER: 8,
            SatelliteType.MILITARY: 9,
            SatelliteType.COMMERCIAL: 5,
            SatelliteType.AMATEUR: 3,
            SatelliteType.SCIENCE: 7,
        }[sat_type]

    def _upsert_satellite(self, record: dict) -> None:
        satellite = self.db.scalar(select(Satellite).where(Satellite.norad_id == record["norad_id"]))
        if satellite is None:
            satellite = Satellite(**record)
            self.db.add(satellite)
        else:
            # Preserve operator-tuned mission priority across routine TLE refreshes.
            satellite.name = record["name"]
            satellite.tle_line1 = record["tle_line1"]
            satellite.tle_line2 = record["tle_line2"]
            satellite.satellite_type = record["satellite_type"]
            satellite.tle_fetched_at = datetime.now(UTC)
