from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from app import schemas
from app.db.session import get_db
from app.models import Conflict, GroundStation, PassStatus, PassWindow, Satellite
from app.services import pipeline as pipeline_state
from app.services.conflict_resolver import ConflictResolver
from app.services.pass_computation import PassComputationEngine
from app.services.pipeline import run_full_pipeline
from app.services.simulation import SimulationEngine

router = APIRouter(prefix="/api")


@router.get("/passes", response_model=list[schemas.PassOut])
def get_passes(
    satellite_id: int | None = None,
    ground_station_id: int | None = None,
    min_elevation: float | None = Query(default=None, ge=0, le=90),
    db: Session = Depends(get_db),
):
    now = datetime.now(UTC)
    stmt = (
        select(PassWindow)
        .options(joinedload(PassWindow.satellite), joinedload(PassWindow.ground_station))
        .where(PassWindow.aos_time >= now)
        .where(PassWindow.aos_time < now + timedelta(hours=24))
        .order_by(PassWindow.ground_station_id, PassWindow.aos_time)
    )
    if satellite_id:
        stmt = stmt.where(PassWindow.satellite_id == satellite_id)
    if ground_station_id:
        stmt = stmt.where(PassWindow.ground_station_id == ground_station_id)
    if min_elevation is not None:
        stmt = stmt.where(PassWindow.max_elevation_deg >= min_elevation)
    return [_pass_out(pass_window) for pass_window in db.scalars(stmt)]


@router.get("/schedule/daily")
def get_daily_schedule(db: Session = Depends(get_db)):
    # The view centralizes dashboard joins, keeping Angular fast and backend route code small.
    rows = db.execute(text("SELECT * FROM daily_schedule_view WHERE date = CURRENT_DATE ORDER BY ground_station_id, slot_order"))
    return [dict(row._mapping) for row in rows]


@router.get("/conflicts", response_model=list[schemas.ConflictOut])
def get_conflicts(db: Session = Depends(get_db)):
    stmt = (
        select(Conflict)
        .options(
            joinedload(Conflict.winner).joinedload(PassWindow.satellite),
            joinedload(Conflict.winner).joinedload(PassWindow.ground_station),
            joinedload(Conflict.loser).joinedload(PassWindow.satellite),
        )
        .order_by(Conflict.resolved_at.desc())
    )
    return [
        schemas.ConflictOut(
            id=conflict.id,
            pass_id_winner=conflict.pass_id_winner,
            pass_id_loser=conflict.pass_id_loser,
            winner_satellite=conflict.winner.satellite.name,
            loser_satellite=conflict.loser.satellite.name,
            ground_station=conflict.winner.ground_station.name,
            conflict_reason=conflict.conflict_reason,
            resolution_reason=conflict.resolution_reason,
            alternative_window=conflict.alternative_window,
            resolved_at=conflict.resolved_at,
        )
        for conflict in db.scalars(stmt)
    ]


@router.post("/groundstations", response_model=schemas.GroundStationOut)
def create_ground_station(payload: schemas.GroundStationCreate, db: Session = Depends(get_db)):
    station = GroundStation(**payload.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@router.get("/groundstations", response_model=list[schemas.GroundStationOut])
def list_ground_stations(db: Session = Depends(get_db)):
    return list(db.scalars(select(GroundStation).order_by(GroundStation.name)))


@router.get("/satellites", response_model=list[schemas.SatelliteOut])
def list_satellites(db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    satellites = db.scalars(select(Satellite).order_by(Satellite.satellite_type, Satellite.name))
    return [
        schemas.SatelliteOut(
            id=sat.id,
            norad_id=sat.norad_id,
            name=sat.name,
            mission_priority=sat.mission_priority,
            satellite_type=sat.satellite_type,
            tle_fetched_at=sat.tle_fetched_at,
            tle_age_hours=round((now - sat.tle_fetched_at).total_seconds() / 3600, 2),
        )
        for sat in satellites
    ]


@router.put("/satellites/{satellite_id}/priority", response_model=schemas.SatelliteOut)
def update_satellite_priority(satellite_id: int, payload: schemas.PriorityUpdate, db: Session = Depends(get_db)):
    satellite = db.get(Satellite, satellite_id)
    if satellite is None:
        raise HTTPException(status_code=404, detail="Satellite not found")
    satellite.mission_priority = payload.mission_priority
    db.commit()
    db.refresh(satellite)
    now = datetime.now(UTC)
    return schemas.SatelliteOut(
        id=satellite.id,
        norad_id=satellite.norad_id,
        name=satellite.name,
        mission_priority=satellite.mission_priority,
        satellite_type=satellite.satellite_type,
        tle_fetched_at=satellite.tle_fetched_at,
        tle_age_hours=round((now - satellite.tle_fetched_at).total_seconds() / 3600, 2),
    )


@router.post("/replay")
async def replay(payload: schemas.ReplayRequest | None = None, db: Session = Depends(get_db)):
    if payload is None:
        result = await run_full_pipeline(db, force_tle=True)
        return {"mode": "live_recompute", **result}
    return SimulationEngine(db).replay(payload.date, payload.ground_station_id)


@router.post("/conflicts/{conflict_id}/resolve")
def rerun_conflict_resolution(conflict_id: int, db: Session = Depends(get_db)):
    if db.get(Conflict, conflict_id) is None:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return ConflictResolver(db).resolve_day()


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db)):
    today_start = datetime.combine(datetime.now(UTC).date(), datetime.min.time(), tzinfo=UTC)
    tomorrow = today_start + timedelta(days=1)
    total_passes = db.scalar(select(func.count()).select_from(PassWindow).where(PassWindow.aos_time >= today_start, PassWindow.aos_time < tomorrow)) or 0
    conflicts = db.scalar(select(func.count()).select_from(Conflict)) or 0
    resolved = db.scalar(select(func.count()).select_from(Conflict).where(Conflict.resolved_at.is_not(None))) or 0
    rate = round((resolved / conflicts) * 100, 2) if conflicts else 100.0
    return schemas.StatsOut(
        total_passes_today=total_passes,
        conflicts_detected=conflicts,
        conflicts_resolved=resolved,
        resolution_rate_percent=rate,
        last_pipeline_seconds=pipeline_state.last_pipeline_seconds,
    )


@router.get("/positions")
def get_current_positions(db: Session = Depends(get_db)):
    return PassComputationEngine(db).current_positions()


def _pass_out(pass_window: PassWindow) -> schemas.PassOut:
    return schemas.PassOut(
        id=pass_window.id,
        satellite_id=pass_window.satellite_id,
        satellite_name=pass_window.satellite.name,
        ground_station_id=pass_window.ground_station_id,
        ground_station_name=pass_window.ground_station.name,
        aos_time=pass_window.aos_time,
        los_time=pass_window.los_time,
        max_elevation_deg=pass_window.max_elevation_deg,
        duration_seconds=pass_window.duration_seconds,
        status=pass_window.status,
        mission_priority=pass_window.satellite.mission_priority,
        satellite_type=pass_window.satellite.satellite_type,
    )
