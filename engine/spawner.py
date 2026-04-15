from __future__ import annotations

import datetime
import random
from dataclasses import dataclass
from typing import Dict, List

from domain.air_object import AirObject
from domain.enums import DespawnReason
from generator.flight_factory import FlightFactory

from .config import AreaConfig, TransientConfig


@dataclass
class TransientMeta:
    expires_at: datetime.datetime
    remaining_km: float


class TransientSpawner:
    """
    Генерирует и удаляет краткоживущие реальные явления в truth-layer:
      * стаи птиц,
      * погодные ячейки,
      * аэростаты и похожие transient-объекты.
    """

    def __init__(self, area: AreaConfig, transient: TransientConfig):
        self._area = area
        self._cfg = transient
        self._meta_by_id: Dict[str, TransientMeta] = {}

    def initial_objects(self, current_time: datetime.datetime) -> List[AirObject]:
        objects: List[AirObject] = []
        for _ in range(self._cfg.initial_objects):
            objects.extend(self._spawn_one(current_time))
        return objects

    def maybe_spawn(self, current_time: datetime.datetime) -> List[AirObject]:
        if not self._cfg.enabled:
            return []
        if random.random() >= self._cfg.spawn_rate_per_tick:
            return []
        return self._spawn_one(current_time)

    def _spawn_one(self, current_time: datetime.datetime) -> List[AirObject]:
        obj = FlightFactory.create_transient_object()
        lat, lon, altitude, speed, heading = FlightFactory.sample_object_position(
            area=self._area,
            platform_class=obj.platform_class,
        )
        obj.update_position(
            lat=lat,
            lon=lon,
            altitude=altitude,
            speed=speed,
            heading=heading,
            timestamp=current_time,
        )

        ttl = random.randint(self._cfg.ttl_seconds_min, self._cfg.ttl_seconds_max)
        travel_km = random.uniform(self._cfg.travel_km_min, self._cfg.travel_km_max)
        self._meta_by_id[obj.object_id] = TransientMeta(
            expires_at=current_time + datetime.timedelta(seconds=ttl),
            remaining_km=travel_km,
        )
        return [obj]

    def consume_distance(self, obj: AirObject, distance_km: float) -> None:
        meta = self._meta_by_id.get(obj.object_id)
        if meta is None:
            return
        meta.remaining_km -= max(0.0, distance_km)

    def is_transient(self, obj: AirObject) -> bool:
        return obj.object_id in self._meta_by_id

    def should_despawn(self, obj: AirObject, current_time: datetime.datetime, area: AreaConfig) -> bool:
        return self.despawn_reason(obj, current_time=current_time, area=area) is not None

    def despawn_reason(
        self,
        obj: AirObject,
        current_time: datetime.datetime,
        area: AreaConfig,
    ) -> DespawnReason | None:
        meta = self._meta_by_id.get(obj.object_id)
        if meta is None:
            return None
        if current_time >= meta.expires_at:
            return DespawnReason.TRANSIENT_EXPIRED
        if meta.remaining_km <= 0:
            return DespawnReason.TRANSIENT_DISTANCE_EXHAUSTED
        last = obj.latest_position()
        if last is None:
            return DespawnReason.TRANSIENT_EXPIRED
        if not area.contains(last.lat, last.lon):
            return DespawnReason.TRANSIENT_LEFT_AREA
        return None

    def despawn(self, obj: AirObject) -> None:
        self._meta_by_id.pop(obj.object_id, None)
