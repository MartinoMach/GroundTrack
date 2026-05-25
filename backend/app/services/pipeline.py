from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.conflict_resolver import ConflictResolver
from app.services.pass_computation import PassComputationEngine
from app.services.tle_ingestion import TleIngestionService

last_pipeline_seconds: float | None = None


async def run_full_pipeline(db: Session, force_tle: bool = False) -> dict:
    global last_pipeline_seconds
    tle_service = TleIngestionService(db)
    tle_count = await (tle_service.refresh_all() if force_tle else tle_service.refresh_if_stale())
    pass_engine = PassComputationEngine(db)
    pass_engine.ensure_default_ground_stations()
    compute = pass_engine.compute_next_24h()
    resolution = ConflictResolver(db).resolve_day()
    last_pipeline_seconds = compute["seconds"] + resolution["seconds"]
    return {"tle_records_updated": tle_count, "compute": compute, "resolution": resolution}
