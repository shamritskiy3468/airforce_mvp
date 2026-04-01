from __future__ import annotations

import datetime
import random
from typing import Dict, List, Optional

from domain.air_object import AirObject, Position
from domain.flight import Flight
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import haversine_distance

from .config import SimulationConfig
from .events import PositionEvent
from .sinks import EventSink
from .spawner import TransientSpawner


class SimulationEngine:
    """
    Центральный orchestration-слой симуляции:
      * конфиг,
      * transient spawner (spawn/despawn),
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
        self._spawner = TransientSpawner(area=config.area, transient=config.transient)
        self._last_emitted_position_by_id: Dict[str, Position] = {}
        self._last_emitted_time_by_id: Dict[str, datetime.datetime] = {}

        if config.seed is not None:
            random.seed(config.seed)

        initial_transients = self._spawner.initial_objects(self.current_time)
        for obj in initial_transients:
            self.objects.append(obj)
            self.navigation_policies[obj.object_id] = self._default_policy_for(obj)

    def step(self) -> int:
        """
        Делает один тик симуляции и публикует события.
        Возвращает число опубликованных событий.
        """

        dt = self.config.time.tick_seconds

        # 1) Спавним transient-явления (если надо)
        spawned = self._spawner.maybe_spawn(self.current_time)
        for obj in spawned:
            self.objects.append(obj)
            self.navigation_policies[obj.object_id] = self._default_policy_for(obj)

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

            if not self.config.area.contains(last_after.lat, last_after.lon):
                continue

            if self._spawner.is_transient(obj) and last_before is not None:
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
                    scenario_bucket=obj.scenario_bucket,
                    platform_class=obj.platform_class,
                    mission_profile=obj.mission_profile,
                    truth_affiliation=obj.truth_affiliation,
                    cooperation_status=obj.cooperation_status,
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

        # 3) Удаляем transient-явления по TTL/дистанции/выходу за границы
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
        configured = self.config.events.emit_interval_seconds_by_type.get(obj.platform_class.value)
        if configured is None:
            return self.config.time.tick_seconds
        return max(self.config.time.tick_seconds, configured)

    def _default_policy_for(self, obj: AirObject):
        from engine.navigation.random_policy import RandomNavigationPolicy
        from engine.navigation.route_policy import RouteNavigationPolicy

        if isinstance(obj, Flight) and obj.route is not None:
            return RouteNavigationPolicy()
        return RandomNavigationPolicy(area=self.config.area)
