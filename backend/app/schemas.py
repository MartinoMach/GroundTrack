from datetime import date, datetime

from pydantic import BaseModel, Field


class GroundStationCreate(BaseModel):
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    elevation_m: float = 0


class GroundStationOut(GroundStationCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SatelliteOut(BaseModel):
    id: int
    norad_id: int
    name: str
    mission_priority: int
    satellite_type: str
    tle_fetched_at: datetime
    tle_age_hours: float


class PriorityUpdate(BaseModel):
    mission_priority: int = Field(ge=1, le=10)


class PassOut(BaseModel):
    id: int
    satellite_id: int
    satellite_name: str
    ground_station_id: int
    ground_station_name: str
    aos_time: datetime
    los_time: datetime
    max_elevation_deg: float
    duration_seconds: int
    status: str
    mission_priority: int
    satellite_type: str


class ConflictOut(BaseModel):
    id: int
    pass_id_winner: int
    pass_id_loser: int
    winner_satellite: str
    loser_satellite: str
    ground_station: str
    conflict_reason: str
    resolution_reason: str
    alternative_window: str | None
    resolved_at: datetime


class ReplayRequest(BaseModel):
    date: date
    ground_station_id: int | None = None


class StatsOut(BaseModel):
    total_passes_today: int
    conflicts_detected: int
    conflicts_resolved: int
    resolution_rate_percent: float
    last_pipeline_seconds: float | None = None
