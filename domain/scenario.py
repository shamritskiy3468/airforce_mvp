from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .enums import (
    CooperationStatus,
    FlightCategory,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    TruthAffiliation,
)
from .route import Route, Waypoint

NavigationMode = Literal["route", "free", "playback"]


@dataclass(frozen=True)
class RouteSpec:
    waypoints: list[Waypoint] = field(default_factory=list)

    def to_route(self) -> Route:
        if len(self.waypoints) < 2:
            raise ValueError("RouteSpec must contain at least 2 waypoints")
        return Route(
            origin=self.waypoints[0],
            destination=self.waypoints[-1],
            waypoints=self.waypoints[1:-1],
        )


@dataclass(frozen=True)
class TrackPointSpec:
    lat: float
    lon: float
    altitude: float
    timestamp: Optional[str] = None
    offset_seconds: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None


@dataclass(frozen=True)
class TrackSpec:
    points: list[TrackPointSpec] = field(default_factory=list)

    def validate(self) -> None:
        if not self.points:
            raise ValueError("TrackSpec must contain at least 1 point")
        for point in self.points:
            if point.timestamp is None and point.offset_seconds is None:
                raise ValueError("Each TrackSpec point must have either timestamp or offset_seconds")


@dataclass(frozen=True)
class ScenarioObjectSpec:
    object_id: Optional[str] = None
    callsign: Optional[str] = None
    flight_category: FlightCategory = FlightCategory.UNKNOWN
    origin_label: Optional[str] = None
    destination_label: Optional[str] = None
    scenario_bucket: ScenarioBucket = ScenarioBucket.UNSCHEDULED_TRAFFIC
    platform_class: PlatformClass = PlatformClass.UNKNOWN
    mission_profile: MissionProfile = MissionProfile.TRANSIT
    truth_affiliation: TruthAffiliation = TruthAffiliation.NEUTRAL
    cooperation_status: CooperationStatus = CooperationStatus.SILENT
    navigation_mode: NavigationMode = "route"
    route: Optional[RouteSpec] = None
    route_csv_path: Optional[str] = None
    track: Optional[TrackSpec] = None
    track_csv_path: Optional[str] = None
    initial_position: Optional[Waypoint] = None
    initial_speed_kmh: Optional[float] = None
    initial_heading_deg: Optional[float] = None
    max_lifetime_seconds: Optional[int] = None
    default_route_altitude_m: float = 0.0

    def validate(self) -> None:
        if self.navigation_mode == "route":
            if self.route is None and self.route_csv_path is None:
                raise ValueError("Route navigation requires route points or route_csv_path")
            if self.track is not None or self.track_csv_path is not None:
                raise ValueError("Route navigation cannot use track/track_csv_path")
        if self.navigation_mode == "free" and self.initial_position is None:
            raise ValueError("Free navigation requires initial_position")
        if self.navigation_mode == "playback":
            if self.track is None and self.track_csv_path is None:
                raise ValueError("Playback navigation requires track points or track_csv_path")
            if self.route is not None or self.route_csv_path is not None:
                raise ValueError("Playback navigation cannot use route/route_csv_path")
            if self.track is not None:
                self.track.validate()


@dataclass(frozen=True)
class ScenarioSpec:
    name: str = "unnamed_scenario"
    objects: list[ScenarioObjectSpec] = field(default_factory=list)

    def validate(self) -> None:
        for obj in self.objects:
            obj.validate()
