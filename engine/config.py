from __future__ import annotations

from dataclasses import dataclass
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
class NoiseConfig:
    # Config класс для "Шумов" 
    enabled: bool = False # включен ли генератор шумов чтобы явно не ковырять коэфициенты
    spawn_rate_per_tick: float = 0.2 # сколько шумовых объектов спавнить за тик (в среднем).
    ttl_seconds_min: int = 60 # минимальное время жизни объекта
    ttl_seconds_max: int = 300 # максимальное время жизни объекта
    travel_km_min: float = 5.0 # минимальное расстояние, которое ШУМ объект должен пролететь
    travel_km_max: float = 70.0 # максимальное расстояние, которое ШУМ объект может пролететь


@dataclass(frozen=True)
class TimeConfig:
    # Управление временем симуляции
    tick_seconds: int = 5 # 1.0 = realtime (1 sec real = 1 sec sim), >1 ускорение, <1 замедление
    time_scale: float = 20.0
    max_steps: int = 100000 # защита от бесконечности

@dataclass(frozen=True)
class FleetConfig:
    planned_flights: int = 0
    random_objects: int = 0


@dataclass(frozen=True)
class RuntimeConfig:
    """
    Управление режимом исполнения симуляции.

    realtime=True означает, что генерация событий "пейсится" под реальное время:
      real_step_seconds = tick_seconds / time_scale
    """

    realtime: bool = False

# Конфиг для симуляции целиком
@dataclass(frozen=True)
class SimulationConfig:
    seed: Optional[int]
    time: TimeConfig
    area: AreaConfig
    noise: NoiseConfig
    fleet: FleetConfig
    runtime: RuntimeConfig

