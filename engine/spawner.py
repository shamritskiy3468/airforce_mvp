from __future__ import annotations

import datetime
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from domain.air_object import AirObject
from domain.enums import AirObjectType

from .config import AreaConfig, NoiseConfig


@dataclass
class NoiseMeta:
    """
    Метаданные для "шумовой" цели, чтобы понимать, когда её удалить.
    """

    expires_at: datetime.datetime
    remaining_km: float


class NoiseSpawner:
    """
    Спавнит и удаляет шумовые объекты:
      * появляются "из ниоткуда" в пределах области,
      * живут TTL,
      * либо исчезают после прохождения travel_km.
    """

    def __init__(self, area: AreaConfig, noise: NoiseConfig):
        self._area = area
        self._cfg = noise
        self._meta_by_id: Dict[str, NoiseMeta] = {}

    def maybe_spawn(self, current_time: datetime.datetime) -> List[AirObject]:
        spawned: List[AirObject] = []

        if not self._cfg.enabled:
            return spawned

        # Простейшая модель: с вероятностью spawn_rate_per_tick создаём 1 шумовую цель.
        if random.random() >= self._cfg.spawn_rate_per_tick:
            return spawned

        obj_type = random.choice(
            [
                AirObjectType.BIRD,
                AirObjectType.CLOUD,
                AirObjectType.DRONE,
                AirObjectType.UAV,
                AirObjectType.HELICOPTER,
            ]
        )
        obj = AirObject(type=obj_type)

        lat = random.uniform(self._area.min_lat, self._area.max_lat)
        lon = random.uniform(self._area.min_lon, self._area.max_lon)

        # altitude: очень грубо по типу
        if obj_type in (AirObjectType.CLOUD,):
            altitude = random.uniform(2000, 9000)
        elif obj_type in (AirObjectType.BIRD,):
            altitude = random.uniform(50, 300)
        elif obj_type in (AirObjectType.DRONE, AirObjectType.UAV):
            altitude = random.uniform(100, 2000)
        else:
            altitude = random.uniform(300, 5000)

        obj.update_position(lat=lat, lon=lon, altitude=float(altitude), timestamp=current_time)

        ttl = random.randint(self._cfg.ttl_seconds_min, self._cfg.ttl_seconds_max)
        travel_km = random.uniform(self._cfg.travel_km_min, self._cfg.travel_km_max)
        self._meta_by_id[obj.object_id] = NoiseMeta(
            expires_at=current_time + datetime.timedelta(seconds=ttl),
            remaining_km=travel_km,
        )

        spawned.append(obj)
        return spawned

    def consume_distance(self, obj: AirObject, distance_km: float) -> None:
        meta = self._meta_by_id.get(obj.object_id)
        if meta is None:
            return
        meta.remaining_km -= max(0.0, distance_km)

    def is_noise(self, obj: AirObject) -> bool:
        return obj.object_id in self._meta_by_id

    def should_despawn(self, obj: AirObject, current_time: datetime.datetime, area: AreaConfig) -> bool:
        meta = self._meta_by_id.get(obj.object_id)
        if meta is None:
            return False

        if current_time >= meta.expires_at:
            return True

        if meta.remaining_km <= 0:
            return True

        last = obj.latest_position()
        if last is None:
            return True

        if not area.contains(last.lat, last.lon):
            return True

        return False

    def despawn(self, obj: AirObject) -> None:
        self._meta_by_id.pop(obj.object_id, None)

