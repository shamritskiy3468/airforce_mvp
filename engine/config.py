from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AreaConfig:
    # Границы области симуляции

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    def contains(self, lat: float, lon: float) -> bool:
        return (self.min_lat <= lat <= self.max_lat) and (self.min_lon <= lon <= self.max_lon)


@dataclass(frozen=True)
class TransientConfig:
    enabled: bool = False
    initial_objects: int = 0
    spawn_rate_per_tick: float = 0.0
    ttl_seconds_min: int = 60
    ttl_seconds_max: int = 300
    travel_km_min: float = 5.0
    travel_km_max: float = 70.0


@dataclass(frozen=True)
class TimeConfig:
    # Управление временем симуляции
    tick_seconds: int = 5 # 1.0 = realtime (1 sec real = 1 sec sim), >1 ускорение, <1 замедление
    time_scale: float = 20.0
    max_steps: Optional[int] = 100000 # None = бесконечный режим

@dataclass(frozen=True)
class FleetConfig:
    scheduled_traffic: int = 0
    unscheduled_traffic: int = 0
    restrict_airport_pairs_to_area: bool = True


@dataclass(frozen=True)
class RuntimeConfig:
    """
    Управление режимом исполнения симуляции.

    realtime=True означает, что генерация событий "пейсится" под реальное время:
      real_step_seconds = tick_seconds / time_scale
    """

    realtime: bool = False
    progress_every_steps: int = 500
    startup_spread_seconds: int = 0


@dataclass(frozen=True)
class EventConfig:
    emit_interval_seconds_by_type: dict[str, int] = field(default_factory=dict)
    emit_when_stationary: bool = False # нужно ли спамить стоячие объекты (например, вертолеты на земле) - скорее всего нет :)
    publish_outside_area_for_scheduled: bool = True

# Конфиг для симуляции целиком
@dataclass(frozen=True)
class SimulationConfig:
    seed: Optional[int]
    time: TimeConfig
    area: AreaConfig
    transient: TransientConfig
    fleet: FleetConfig
    runtime: RuntimeConfig
    events: EventConfig = field(default_factory=EventConfig)
