from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Iterable

from domain.air_object import AirObject
from domain.enums import (
    CooperationStatus,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    TruthAffiliation,
)
from domain.flight import Flight
from domain.playback_object import PlaybackObject
from domain.route import Waypoint
from domain.scenario import (
    RouteSpec,
    ScenarioObjectSpec,
    ScenarioSpec,
    TrackPointSpec,
    TrackSpec,
)
from domain.track import Track, TrackPoint
from helpers.csv2route import Csv2Route
from helpers.csv2track import Csv2Track


class ScenarioLoader:
    @classmethod
    def load_spec(cls, path: str | Path) -> ScenarioSpec:
        scenario_path = Path(path)
        with scenario_path.open("r", encoding="utf-8") as infile:
            payload = json.load(infile)

        objects = [
            cls._parse_object_spec(item)
            for item in payload.get("objects", [])
        ]
        spec = ScenarioSpec(
            name=payload.get("name", scenario_path.stem),
            objects=objects,
        )
        spec.validate()
        return spec

    @classmethod
    def load_objects(
        cls,
        paths: Iterable[str | Path],
        start_time: datetime.datetime,
    ) -> list[AirObject]:
        objects: list[AirObject] = []
        for raw_path in paths:
            scenario_path = Path(raw_path)
            spec = cls.load_spec(scenario_path)
            objects.extend(
                cls.materialize(spec=spec, scenario_path=scenario_path, start_time=start_time)
            )
        return objects

    @classmethod
    def materialize(
        cls,
        spec: ScenarioSpec,
        scenario_path: str | Path,
        start_time: datetime.datetime,
    ) -> list[AirObject]:
        materialized: list[AirObject] = []
        base_path = Path(scenario_path).parent

        for obj_spec in spec.objects:
            route = cls._resolve_route(obj_spec, base_path=base_path)
            track = cls._resolve_track(obj_spec, base_path=base_path, start_time=start_time)

            if track is not None:
                obj = PlaybackObject(
                    object_id=obj_spec.object_id or str(uuid.uuid4()),
                    scenario_bucket=obj_spec.scenario_bucket,
                    platform_class=obj_spec.platform_class,
                    mission_profile=obj_spec.mission_profile,
                    truth_affiliation=obj_spec.truth_affiliation,
                    cooperation_status=obj_spec.cooperation_status,
                    track=track,
                )
                first_point = track.points[0]
                if first_point.timestamp <= start_time:
                    initial_position = Waypoint(
                        lat=first_point.lat,
                        lon=first_point.lon,
                        altitude=first_point.altitude,
                    )
                    initial_speed_kmh = first_point.speed_kmh
                    initial_heading_deg = first_point.heading_deg
                    initial_timestamp = first_point.timestamp
                else:
                    initial_position = None
                    initial_speed_kmh = None
                    initial_heading_deg = None
                    initial_timestamp = None
            elif route is not None:
                obj = Flight(
                    object_id=obj_spec.object_id or str(uuid.uuid4()),
                    scenario_bucket=obj_spec.scenario_bucket,
                    platform_class=obj_spec.platform_class,
                    mission_profile=obj_spec.mission_profile,
                    truth_affiliation=obj_spec.truth_affiliation,
                    cooperation_status=obj_spec.cooperation_status,
                    route=route,
                    callsign=obj_spec.callsign,
                )
                initial_position = obj_spec.initial_position or route.origin
                initial_speed_kmh = obj_spec.initial_speed_kmh
                initial_heading_deg = obj_spec.initial_heading_deg
                initial_timestamp = start_time
            else:
                obj = AirObject(
                    object_id=obj_spec.object_id or str(uuid.uuid4()),
                    scenario_bucket=obj_spec.scenario_bucket,
                    platform_class=obj_spec.platform_class,
                    mission_profile=obj_spec.mission_profile,
                    truth_affiliation=obj_spec.truth_affiliation,
                    cooperation_status=obj_spec.cooperation_status,
                )
                initial_position = obj_spec.initial_position
                initial_speed_kmh = obj_spec.initial_speed_kmh
                initial_heading_deg = obj_spec.initial_heading_deg
                initial_timestamp = start_time

            if initial_position is not None:
                obj.update_position(
                    lat=initial_position.lat,
                    lon=initial_position.lon,
                    altitude=initial_position.altitude,
                    speed=initial_speed_kmh,
                    heading=initial_heading_deg,
                    timestamp=initial_timestamp,
                )

            materialized.append(obj)

        return materialized

    @staticmethod
    def _parse_object_spec(payload: dict) -> ScenarioObjectSpec:
        route_payload = payload.get("route")
        route_spec = None
        if route_payload is not None:
            route_spec = RouteSpec(
                waypoints=[
                    ScenarioLoader._parse_waypoint(item)
                    for item in route_payload.get("waypoints", [])
                ]
            )

        track_payload = payload.get("track")
        track_spec = None
        if track_payload is not None:
            track_spec = TrackSpec(
                points=[
                    ScenarioLoader._parse_track_point(item)
                    for item in track_payload.get("points", [])
                ]
            )

        initial_position_payload = payload.get("initial_position")
        return ScenarioObjectSpec(
            object_id=payload.get("object_id"),
            callsign=payload.get("callsign"),
            scenario_bucket=ScenarioLoader._parse_enum(
                ScenarioBucket,
                payload.get("scenario_bucket", ScenarioBucket.UNSCHEDULED_TRAFFIC.value),
                field_name="scenario_bucket",
            ),
            platform_class=ScenarioLoader._parse_enum(
                PlatformClass,
                payload.get("platform_class", PlatformClass.UNKNOWN.value),
                field_name="platform_class",
            ),
            mission_profile=ScenarioLoader._parse_enum(
                MissionProfile,
                payload.get("mission_profile", MissionProfile.TRANSIT.value),
                field_name="mission_profile",
            ),
            truth_affiliation=ScenarioLoader._parse_enum(
                TruthAffiliation,
                payload.get("truth_affiliation", TruthAffiliation.NEUTRAL.value),
                field_name="truth_affiliation",
            ),
            cooperation_status=ScenarioLoader._parse_enum(
                CooperationStatus,
                payload.get("cooperation_status", CooperationStatus.SILENT.value),
                field_name="cooperation_status",
            ),
            navigation_mode=payload.get("navigation_mode", "route"),
            route=route_spec,
            route_csv_path=payload.get("route_csv_path"),
            track=track_spec,
            track_csv_path=payload.get("track_csv_path"),
            initial_position=(
                ScenarioLoader._parse_waypoint(initial_position_payload)
                if initial_position_payload is not None
                else None
            ),
            initial_speed_kmh=payload.get("initial_speed_kmh"),
            initial_heading_deg=payload.get("initial_heading_deg"),
            default_route_altitude_m=float(payload.get("default_route_altitude_m", 0.0)),
        )

    @staticmethod
    def _resolve_route(obj_spec: ScenarioObjectSpec, base_path: Path):
        if obj_spec.route is not None:
            return obj_spec.route.to_route()
        if obj_spec.route_csv_path is None:
            return None

        csv_path = Path(obj_spec.route_csv_path)
        if not csv_path.is_absolute():
            csv_path = base_path / csv_path

        return Csv2Route(
            filename=str(csv_path),
            default_altitude_m=obj_spec.default_route_altitude_m,
        ).route

    @classmethod
    def _resolve_track(
        cls,
        obj_spec: ScenarioObjectSpec,
        base_path: Path,
        start_time: datetime.datetime,
    ) -> Track | None:
        track_spec = obj_spec.track
        if track_spec is None and obj_spec.track_csv_path is not None:
            csv_path = Path(obj_spec.track_csv_path)
            if not csv_path.is_absolute():
                csv_path = base_path / csv_path
            track_spec = Csv2Track(filename=str(csv_path)).track_spec

        if track_spec is None:
            return None

        points: list[TrackPoint] = []
        for point in track_spec.points:
            points.append(
                TrackPoint(
                    timestamp=cls._resolve_point_timestamp(point, start_time=start_time),
                    lat=point.lat,
                    lon=point.lon,
                    altitude=point.altitude,
                    speed_kmh=point.speed_kmh,
                    heading_deg=point.heading_deg,
                )
            )

        return Track(points=points)

    @staticmethod
    def _parse_waypoint(payload: dict) -> Waypoint:
        return Waypoint(
            lat=float(payload["lat"]),
            lon=float(payload["lon"]),
            altitude=float(payload.get("altitude", 0.0)),
        )

    @staticmethod
    def _parse_track_point(payload: dict) -> TrackPointSpec:
        return TrackPointSpec(
            lat=float(payload["lat"]),
            lon=float(payload["lon"]),
            altitude=float(payload.get("altitude", 0.0)),
            timestamp=payload.get("timestamp"),
            offset_seconds=(
                float(payload["offset_seconds"])
                if payload.get("offset_seconds") not in (None, "")
                else None
            ),
            speed_kmh=(
                float(payload["speed_kmh"])
                if payload.get("speed_kmh") not in (None, "")
                else None
            ),
            heading_deg=(
                float(payload["heading_deg"])
                if payload.get("heading_deg") not in (None, "")
                else None
            ),
        )

    @staticmethod
    def _resolve_point_timestamp(
        point: TrackPointSpec,
        start_time: datetime.datetime,
    ) -> datetime.datetime:
        if point.timestamp is not None:
            parsed = datetime.datetime.fromisoformat(point.timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None and start_time.tzinfo is not None:
                parsed = parsed.replace(tzinfo=start_time.tzinfo)
            return parsed

        if point.offset_seconds is None:
            raise ValueError("Track point must define timestamp or offset_seconds")

        return start_time + datetime.timedelta(seconds=point.offset_seconds)

    @staticmethod
    def _parse_enum(enum_cls, value: str, field_name: str):
        try:
            return enum_cls(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_cls)
            raise ValueError(f"Invalid {field_name}={value!r}. Allowed: {allowed}") from exc
