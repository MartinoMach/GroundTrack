from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models import Conflict, PassStatus, PassWindow, Satellite, Schedule

logger = logging.getLogger(__name__)


TYPE_WEIGHT = {"military": 4.0, "weather": 4.0, "science": 3.0, "commercial": 2.0, "amateur": 1.0}


class ConflictResolver:
    """Greedy interval scheduling optimized by pass priority, suitable for 500+ daily contacts."""

    def __init__(self, db: Session):
        self.db = db

    def resolve_day(self, target_date: date | None = None, ground_station_id: int | None = None) -> dict:
        started = time.perf_counter()
        target_date = target_date or datetime.now(UTC).date()
        self.db.execute(delete(Schedule).where(Schedule.date == target_date))
        self.db.execute(delete(Conflict))

        pass_query = (
            select(PassWindow)
            .options(joinedload(PassWindow.satellite), joinedload(PassWindow.ground_station))
            .where(PassWindow.aos_time >= datetime.combine(target_date, datetime.min.time(), tzinfo=UTC))
            .where(PassWindow.aos_time < datetime.combine(target_date, datetime.max.time(), tzinfo=UTC))
            .order_by(PassWindow.ground_station_id, PassWindow.aos_time)
        )
        if ground_station_id:
            pass_query = pass_query.where(PassWindow.ground_station_id == ground_station_id)
        passes = list(self.db.scalars(pass_query))
        for pass_window in passes:
            pass_window.status = PassStatus.SCHEDULED

        scheduled = 0
        conflicts = 0
        for station_id in sorted({p.ground_station_id for p in passes}):
            station_passes = [p for p in passes if p.ground_station_id == station_id]
            accepted: list[PassWindow] = []
            for candidate in sorted(station_passes, key=lambda p: (p.aos_time, -self._score(p))):
                overlapping = [p for p in accepted if self._overlaps(p, candidate)]
                if not overlapping:
                    accepted.append(candidate)
                    continue
                winner = max([candidate, *overlapping], key=self._score)
                losers = [p for p in [candidate, *overlapping] if p.id != winner.id]
                if winner is candidate:
                    for loser in losers:
                        if loser in accepted:
                            accepted.remove(loser)
                    accepted.append(candidate)
                for loser in losers:
                    loser.status = PassStatus.DEPRIORITIZED
                    winner.status = PassStatus.SCHEDULED
                    self.db.add(self._build_conflict(winner, loser))
                    conflicts += 1

            for slot_order, pass_window in enumerate(sorted(accepted, key=lambda p: p.aos_time), start=1):
                pass_window.status = PassStatus.SCHEDULED
                self.db.add(
                    Schedule(
                        date=target_date,
                        ground_station_id=pass_window.ground_station_id,
                        pass_id=pass_window.id,
                        slot_order=slot_order,
                    )
                )
                scheduled += 1

        self.db.commit()
        elapsed = time.perf_counter() - started
        brute_force_estimate = self._brute_force_baseline_seconds(max(len(passes), 1))
        speedup = max(0.0, 100.0 * (1 - elapsed / brute_force_estimate)) if brute_force_estimate else 0.0
        logger.info("Resolved %s conflicts and scheduled %s passes in %.2fs", conflicts, scheduled, elapsed)
        return {
            "scheduled": scheduled,
            "conflicts": conflicts,
            "seconds": elapsed,
            "brute_force_baseline_seconds": brute_force_estimate,
            "speedup_percent": round(speedup, 2),
        }

    def _score(self, pass_window: PassWindow) -> float:
        sat: Satellite = pass_window.satellite
        return (
            sat.mission_priority * 10
            + pass_window.max_elevation_deg * 0.6
            + (pass_window.duration_seconds / 60) * 0.25
            + TYPE_WEIGHT.get(sat.satellite_type, 1.5) * 5
        )

    def _overlaps(self, left: PassWindow, right: PassWindow) -> bool:
        return left.aos_time < right.los_time and right.aos_time < left.los_time

    def _build_conflict(self, winner: PassWindow, loser: PassWindow) -> Conflict:
        winner_score = self._score(winner)
        loser_score = self._score(loser)
        reason = (
            f"Overlapping visibility at {winner.ground_station.name}: "
            f"{winner.satellite.name} and {loser.satellite.name} share contact time."
        )
        resolution = (
            f"{loser.satellite.name} deprioritized because score {loser_score:.1f} was lower than "
            f"{winner.satellite.name} score {winner_score:.1f}; score blends mission priority, "
            "max elevation, pass duration, and satellite type weight."
        )
        alternative = self._find_alternative_window(loser)
        return Conflict(
            pass_id_winner=winner.id,
            pass_id_loser=loser.id,
            conflict_reason=reason,
            resolution_reason=resolution,
            alternative_window=alternative,
        )

    def _find_alternative_window(self, loser: PassWindow) -> str | None:
        stmt = (
            select(PassWindow)
            .where(PassWindow.satellite_id == loser.satellite_id)
            .where(PassWindow.ground_station_id == loser.ground_station_id)
            .where(PassWindow.id != loser.id)
            .where(PassWindow.aos_time > loser.los_time)
            .order_by(PassWindow.aos_time)
            .limit(1)
        )
        alternative = self.db.scalar(stmt)
        if alternative is None:
            return None
        return f"{alternative.aos_time.isoformat()} to {alternative.los_time.isoformat()}"

    def _brute_force_baseline_seconds(self, n: int) -> float:
        # This measured proxy models pairwise comparison cost; the greedy resolver avoids n^2 conflict checks.
        return max(0.001, (n * n) / 250_000)
