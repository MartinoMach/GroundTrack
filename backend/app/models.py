from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PassStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFLICT = "conflict"
    DEPRIORITIZED = "deprioritized"


class SatelliteType(StrEnum):
    WEATHER = "weather"
    MILITARY = "military"
    COMMERCIAL = "commercial"
    AMATEUR = "amateur"
    SCIENCE = "science"


class GroundStation(Base):
    __tablename__ = "ground_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    elevation_m: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    passes: Mapped[list["PassWindow"]] = relationship(back_populates="ground_station")


class Satellite(Base):
    __tablename__ = "satellites"
    __table_args__ = (UniqueConstraint("norad_id", name="uq_satellites_norad_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    norad_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    tle_line1: Mapped[str] = mapped_column(String(80))
    tle_line2: Mapped[str] = mapped_column(String(80))
    mission_priority: Mapped[int] = mapped_column(Integer, default=5)
    satellite_type: Mapped[str] = mapped_column(String(32), default=SatelliteType.COMMERCIAL)
    tle_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    passes: Mapped[list["PassWindow"]] = relationship(back_populates="satellite")


class PassWindow(Base):
    __tablename__ = "passes"
    __table_args__ = (
        Index("ix_passes_aos_time", "aos_time"),
        Index("ix_passes_satellite_id", "satellite_id"),
        Index("ix_passes_ground_station_id", "ground_station_id"),
        Index("ix_passes_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    satellite_id: Mapped[int] = mapped_column(ForeignKey("satellites.id", ondelete="CASCADE"))
    ground_station_id: Mapped[int] = mapped_column(ForeignKey("ground_stations.id", ondelete="CASCADE"))
    aos_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    los_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_elevation_deg: Mapped[float] = mapped_column(Float)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=PassStatus.SCHEDULED, index=True)

    satellite: Mapped[Satellite] = relationship(back_populates="passes")
    ground_station: Mapped[GroundStation] = relationship(back_populates="passes")


class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    pass_id_winner: Mapped[int] = mapped_column(ForeignKey("passes.id", ondelete="CASCADE"))
    pass_id_loser: Mapped[int] = mapped_column(ForeignKey("passes.id", ondelete="CASCADE"))
    conflict_reason: Mapped[str] = mapped_column(Text)
    resolution_reason: Mapped[str] = mapped_column(Text)
    alternative_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    winner: Mapped[PassWindow] = relationship(foreign_keys=[pass_id_winner])
    loser: Mapped[PassWindow] = relationship(foreign_keys=[pass_id_loser])


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (UniqueConstraint("date", "ground_station_id", "pass_id", name="uq_schedule_day_station_pass"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    ground_station_id: Mapped[int] = mapped_column(ForeignKey("ground_stations.id", ondelete="CASCADE"))
    pass_id: Mapped[int] = mapped_column(ForeignKey("passes.id", ondelete="CASCADE"))
    slot_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    ground_station: Mapped[GroundStation] = relationship()
    pass_window: Mapped[PassWindow] = relationship()
