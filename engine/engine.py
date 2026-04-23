from __future__ import annotations

import datetime
import random
from typing import Dict, List, Optional

from domain.air_object import AirObject, Position
from domain.enums import DespawnReason, FlightState, ScenarioBucket, TruthEventType
from domain.flight import Flight
from domain.playback_object import PlaybackObject
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import haversine_distance

from .config import SimulationConfig
from .events import TruthEvent
from .sinks import EventSink
from .spawner import TransientSpawner


class SimulationEngine:
    """
    Центральный orchestration-слой симуляции:
      * конфиг,
      * transient spawner (spawn/despawn),
      * генерация TruthEvent и отправка в sink,
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
        self._spawned_object_ids: set[str] = set()

        if config.seed is not None:
            random.seed(config.seed)

        for obj in self.objects:
            if obj.object_id not in self.navigation_policies:
                self.navigation_policies[obj.object_id] = self._default_policy_for(obj)

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

        # 2) Двигаем объекты и создаём truth-события
        events = [] # list of [TruthEvent]
        ingest_time = datetime.datetime.now(datetime.timezone.utc) # ingest_time - когда событие "поступило" в систему, может отличаться от event_time, которая внутри события и соответствует симуляционному времени

        for obj in list(self.objects):
            if obj.activation_time is not None and self.current_time < obj.activation_time:
                # Объект ещё "не появился" в мире симуляции.
                continue

            last_before = obj.latest_position()

            if last_before is not None and obj.object_id not in self._spawned_object_ids:
                events.append(
                    self._build_event(
                        obj=obj,
                        pos=last_before,
                        ingest_time=ingest_time,
                        event_type=TruthEventType.SPAWNED,
                    )
                )
                self._mark_spawned(obj, last_before)

            policy = self.navigation_policies.get(obj.object_id)
            if policy is not None:
                policy.move(obj, dt_seconds=dt, current_time=self.current_time)

            last_after = obj.latest_position()
            if last_after is None:
                continue

            if obj.object_id not in self._spawned_object_ids:
                events.append(
                    self._build_event(
                        obj=obj,
                        pos=last_after,
                        ingest_time=ingest_time,
                        event_type=TruthEventType.SPAWNED,
                    )
                )
                self._mark_spawned(obj, last_after)
                continue

            if not self.config.area.contains(last_after.lat, last_after.lon):
                allow_outside = (
                    self.config.events.publish_outside_area_for_scheduled
                    and obj.scenario_bucket == ScenarioBucket.SCHEDULED_TRAFFIC
                )
                if not allow_outside:
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
                self._build_event(
                    obj=obj,
                    pos=last_after,
                    ingest_time=ingest_time,
                    event_type=TruthEventType.POSITION_UPDATED,
                )
            )
            self._last_emitted_position_by_id[obj.object_id] = last_after
            self._last_emitted_time_by_id[obj.object_id] = self.current_time

        # 3) Удаляем transient-явления по TTL/дистанции/выходу за границы
        kept: List[AirObject] = []
        for obj in self.objects:
            despawn_reason = self._despawn_reason_for(obj)
            if despawn_reason is not None:
                last = obj.latest_position()
                if obj.object_id in self._spawned_object_ids and last is not None:
                    events.append(
                        self._build_event(
                            obj=obj,
                            pos=last,
                            ingest_time=ingest_time,
                            event_type=TruthEventType.DESPAWNED,
                            despawn_reason=despawn_reason,
                        )
                    )
                self._spawner.despawn(obj)
                self.navigation_policies.pop(obj.object_id, None)
                self._last_emitted_position_by_id.pop(obj.object_id, None)
                self._last_emitted_time_by_id.pop(obj.object_id, None)
                self._spawned_object_ids.discard(obj.object_id)
                continue
            kept.append(obj)
        self.objects = kept

        # 4) Публикуем события
        self.sink.publish(events)

        # 5) Двигаем симуляционное время
        self.current_time += datetime.timedelta(seconds=dt)

        return len(events)

    def _should_publish(self, obj: AirObject, last_before: Optional[Position], last_after: Position) -> bool:
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

    def _mark_spawned(self, obj: AirObject, pos: Position) -> None:
        self._spawned_object_ids.add(obj.object_id)
        self._last_emitted_position_by_id[obj.object_id] = pos
        self._last_emitted_time_by_id[obj.object_id] = self.current_time

    def _build_event(
        self,
        obj: AirObject,
        pos: Position,
        ingest_time: datetime.datetime,
        event_type: TruthEventType,
        despawn_reason: DespawnReason | None = None,
    ) -> TruthEvent:
        return TruthEvent(
            event_type=event_type,
            object_id=obj.object_id,
            scenario_bucket=obj.scenario_bucket,
            platform_class=obj.platform_class,
            mission_profile=obj.mission_profile,
            truth_affiliation=obj.truth_affiliation,
            cooperation_status=obj.cooperation_status,
            lat=pos.lat,
            lon=pos.lon,
            altitude=pos.altitude,
            heading=pos.heading,
            speed=pos.speed,
            speed_source=pos.speed_source,
            event_time=self.current_time,
            ingest_time=ingest_time,
            despawn_reason=despawn_reason,
        )

    def _despawn_reason_for(self, obj: AirObject) -> DespawnReason | None:
        transient_reason = self._spawner.despawn_reason(
            obj,
            current_time=self.current_time,
            area=self.config.area,
        )
        if transient_reason is not None:
            return transient_reason

        if isinstance(obj, Flight) and obj.state == FlightState.FINISHED:
            return DespawnReason.ROUTE_COMPLETED

        if isinstance(obj, PlaybackObject) and obj.track is not None:
            last = obj.latest_position()
            final_point = obj.track.points[-1]
            if (
                last is not None
                and obj.current_track_idx >= len(obj.track.points) - 1
                and last.timestamp is not None
                and last.timestamp >= final_point.timestamp
            ):
                return DespawnReason.PLAYBACK_COMPLETED

        return None

    def _default_policy_for(self, obj: AirObject):
        from engine.navigation.playback_policy import PlaybackNavigationPolicy
        from engine.navigation.random_policy import RandomNavigationPolicy
        from engine.navigation.route_policy import RouteNavigationPolicy

        if isinstance(obj, PlaybackObject) and obj.track is not None:
            return PlaybackNavigationPolicy()
        if isinstance(obj, Flight) and obj.route is not None:
            return RouteNavigationPolicy()
        return RandomNavigationPolicy(area=self.config.area)
