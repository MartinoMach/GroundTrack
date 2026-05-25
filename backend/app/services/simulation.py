from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Schedule
from app.services.conflict_resolver import ConflictResolver
from app.services.pass_computation import PassComputationEngine


class SimulationEngine:
    """Replay engine reuses stored TLE rows closest to the requested date and regenerates the schedule."""

    def __init__(self, db: Session):
        self.db = db

    def replay(self, target_date, ground_station_id: int | None = None) -> dict:
        start = datetime.combine(target_date, datetime.min.time(), tzinfo=UTC)
        compute_stats = PassComputationEngine(self.db).compute_next_24h(start=start, ground_station_id=ground_station_id)
        resolve_stats = ConflictResolver(self.db).resolve_day(target_date=target_date, ground_station_id=ground_station_id)
        stmt = (
            select(Schedule)
            .where(Schedule.date == target_date)
            .order_by(Schedule.ground_station_id, Schedule.slot_order)
        )
        if ground_station_id:
            stmt = stmt.where(Schedule.ground_station_id == ground_station_id)
        schedule_ids = [row.pass_id for row in self.db.scalars(stmt)]
        return {
            "date": target_date.isoformat(),
            "ground_station_id": ground_station_id,
            "compute": compute_stats,
            "resolution": resolve_stats,
            "scheduled_pass_ids": schedule_ids,
        }
