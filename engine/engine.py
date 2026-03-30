from __future__ import annotations

import datetime
import random
from typing import Dict, List, Optional

from domain.air_object import AirObject, Position
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import haversine_distance

from .config import SimulationConfig
from .events import PositionEvent
from .sinks import EventSink
from .spawner import NoiseSpawner


class SimulationEngine:
    """
    Центральный orchestration-слой симуляции:
      * конфиг,
      * шумовой spawner (spawn/despawn),
      * генерация PositionEvent и отправка в sink,
      * единая точка хранения current_time.
    """

    def __init__(
        self,
        config: SimulationConfig,
        objects: List[AirObject],
        navigation_policies: Dict[str, NavigationPolicy],
        sink: EventSink,
        start_time: datetime.datetime,
    ):
        self.config = config
        self.objects: List[AirObject] = list(objects)
        self.navigation_policies = dict(navigation_policies)
        self.sink = sink

        self.current_time = start_time
        self._spawner = NoiseSpawner(area=config.area, noise=config.noise)
        self._last_emitted_position_by_id: Dict[str, Position] = {}
        self._last_emitted_time_by_id: Dict[str, datetime.datetime] = {}

        if config.seed is not None:
            random.seed(config.seed)

    def step(self) -> int:
        """
        Делает один тик симуляции и публикует события.
        Возвращает число опубликованных событий.
        """

        dt = self.config.time.tick_seconds

        # 1) Спавним шумовые цели (если надо)
        spawned = self._spawner.maybe_spawn(self.current_time)
        for obj in spawned:
            self.objects.append(obj)
            # Для шумов всегда random-policy
            from engine.navigation.random_policy import RandomNavigationPolicy

            self.navigation_policies[obj.object_id] = RandomNavigationPolicy()

        # 2) Двигаем объекты и создаём PositionEvent
        events: List[PositionEvent] = []
        ingest_time = datetime.datetime.now(datetime.timezone.utc)

        for obj in list(self.objects):
            last_before = obj.latest_position()

            policy = self.navigation_policies.get(obj.object_id)
            if policy is not None:
                policy.move(obj, dt_seconds=dt, current_time=self.current_time)

            last_after = obj.latest_position()
            if last_after is None:
                continue

            # Учёт "пройденной дистанции" для шумовых целей
            if self._spawner.is_noise(obj) and last_before is not None:
                dist_km = haversine_distance(
                    last_before.lat,
                    last_before.lon,
                    last_after.lat,
                    last_after.lon,
                )
                self._spawner.consume_distance(obj, dist_km)

            if not self._should_publish(obj, last_before=last_before, last_after=last_after):
                continue

            events.append(
                PositionEvent(
                    object_id=obj.object_id,
                    object_type=obj.type,
                    lat=last_after.lat,
                    lon=last_after.lon,
                    altitude=last_after.altitude,
                    heading=last_after.heading,
                    speed=last_after.speed,
                    speed_source=last_after.speed_source,
                    event_time=self.current_time,
                    ingest_time=ingest_time,
                )
            )
            self._last_emitted_position_by_id[obj.object_id] = last_after
            self._last_emitted_time_by_id[obj.object_id] = self.current_time

        # 3) Удаляем шумовые цели по TTL/дистанции/выходу за границы
        kept: List[AirObject] = []
        for obj in self.objects:
            if self._spawner.should_despawn(obj, current_time=self.current_time, area=self.config.area):
                self._spawner.despawn(obj)
                self.navigation_policies.pop(obj.object_id, None)
                self._last_emitted_position_by_id.pop(obj.object_id, None)
                self._last_emitted_time_by_id.pop(obj.object_id, None)
                continue
            kept.append(obj)
        self.objects = kept

        # 4) Публикуем события
        self.sink.publish(events)

        # 5) Двигаем симуляционное время
        self.current_time += datetime.timedelta(seconds=dt)

        return len(events)

    def _should_publish(
        self,
        obj: AirObject,
        last_before: Optional[Position],
        last_after: Position,
    ) -> bool:
        last_emitted = self._last_emitted_position_by_id.get(obj.object_id)
        last_emitted_time = self._last_emitted_time_by_id.get(obj.object_id)

        if last_emitted is None or last_emitted_time is None:
            return True

        moved_this_step = last_before is not last_after
        if not moved_this_step and not self.config.events.emit_when_stationary:
            return False

        seconds_since_emit = (self.current_time - last_emitted_time).total_seconds()
        required_interval = self._emit_interval_seconds_for(obj)
        return seconds_since_emit >= required_interval

    def _emit_interval_seconds_for(self, obj: AirObject) -> int:
        configured = self.config.events.emit_interval_seconds_by_type.get(obj.type.value)
        if configured is None:
            return self.config.time.tick_seconds
        return max(self.config.time.tick_seconds, configured)
