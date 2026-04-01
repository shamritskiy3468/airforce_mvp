import random
import string
from typing import List, Optional

from domain.air_object import AirObject
from domain.enums import (
    CooperationStatus,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    TruthAffiliation,
)
from domain.flight import Flight
from domain.kinematics import profile_for, sample_altitude_m, sample_speed_kmh
from domain.route import Route, Waypoint
from engine.config import AreaConfig


class FlightFactory:
    """Scenario generator for scheduled traffic, unscheduled traffic, and transient phenomena."""

    @staticmethod
    def generate_scenario(
        scheduled_traffic: int = 2,
        unscheduled_traffic: int = 3,
        transient_phenomena: int = 0,
        area: Optional[AreaConfig] = None,
    ) -> List[AirObject]:
        scenario: List[AirObject] = []

        for _ in range(scheduled_traffic):
            scenario.append(FlightFactory.create_scheduled_traffic(area))

        for _ in range(unscheduled_traffic):
            scenario.append(FlightFactory.create_unscheduled_traffic(area))

        for _ in range(transient_phenomena):
            scenario.append(FlightFactory.create_transient_object())

        return scenario

    @staticmethod
    def create_scheduled_traffic(area: Optional[AreaConfig]) -> AirObject:
        platform_class = random.choices(
            population=[
                PlatformClass.FIXED_WING_AIRCRAFT,
                PlatformClass.ROTARY_WING_AIRCRAFT,
                PlatformClass.MULTIROTOR_UAV,
            ],
            weights=[0.75, 0.15, 0.10],
            k=1,
        )[0]
        mission_profile = random.choices(
            population=[MissionProfile.TRANSIT, MissionProfile.TRAINING],
            weights=[0.85, 0.15],
            k=1,
        )[0]
        route = FlightFactory.create_area_transit_route(area, platform_class) if area else FlightFactory.create_demo_route(platform_class)
        return FlightFactory.create_routed_object(
            scenario_bucket=ScenarioBucket.SCHEDULED_TRAFFIC,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=random.choice([TruthAffiliation.CIVILIAN, TruthAffiliation.FRIENDLY]),
            cooperation_status=CooperationStatus.COOPERATIVE,
            route=route,
            callsign=FlightFactory._generate_callsign(prefix="ST"),
        )

    @staticmethod
    def create_unscheduled_traffic(area: Optional[AreaConfig]) -> AirObject:
        platform_class = random.choices(
            population=[
                PlatformClass.FIXED_WING_AIRCRAFT,
                PlatformClass.ROTARY_WING_AIRCRAFT,
                PlatformClass.FIXED_WING_UAV,
                PlatformClass.MULTIROTOR_UAV,
            ],
            weights=[0.30, 0.20, 0.30, 0.20],
            k=1,
        )[0]

        mission_by_platform = {
            PlatformClass.FIXED_WING_AIRCRAFT: [MissionProfile.PATROL, MissionProfile.RECON, MissionProfile.BORDER_PENETRATION],
            PlatformClass.ROTARY_WING_AIRCRAFT: [MissionProfile.PATROL, MissionProfile.LOITER, MissionProfile.RECON],
            PlatformClass.FIXED_WING_UAV: [MissionProfile.RECON, MissionProfile.LOITER, MissionProfile.BORDER_PENETRATION],
            PlatformClass.MULTIROTOR_UAV: [MissionProfile.LOITER, MissionProfile.RECON],
        }
        mission_profile = random.choice(mission_by_platform[platform_class])
        truth_affiliation = random.choices(
            population=[TruthAffiliation.ADVERSARY, TruthAffiliation.NEUTRAL],
            weights=[0.7, 0.3],
            k=1,
        )[0]
        cooperation_status = random.choice([CooperationStatus.NON_COOPERATIVE, CooperationStatus.SILENT])

        should_route = area is not None and (
            platform_class in (PlatformClass.FIXED_WING_AIRCRAFT, PlatformClass.FIXED_WING_UAV)
            or mission_profile == MissionProfile.BORDER_PENETRATION
        )

        if should_route:
            route = FlightFactory.create_area_transit_route(area, platform_class)
            return FlightFactory.create_routed_object(
                scenario_bucket=ScenarioBucket.UNSCHEDULED_TRAFFIC,
                platform_class=platform_class,
                mission_profile=mission_profile,
                truth_affiliation=truth_affiliation,
                cooperation_status=cooperation_status,
                route=route,
                callsign=FlightFactory._generate_callsign(prefix="UT"),
            )

        return AirObject(
            scenario_bucket=ScenarioBucket.UNSCHEDULED_TRAFFIC,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=truth_affiliation,
            cooperation_status=cooperation_status,
        )

    @staticmethod
    def create_transient_object() -> AirObject:
        platform_class = random.choices(
            population=[
                PlatformClass.BIRD_FLOCK,
                PlatformClass.WEATHER_CELL,
                PlatformClass.BALLOON,
            ],
            weights=[0.5, 0.35, 0.15],
            k=1,
        )[0]

        mission_profile = (
            MissionProfile.WEATHER_DRIFT
            if platform_class in (PlatformClass.WEATHER_CELL, PlatformClass.BALLOON)
            else MissionProfile.LOITER
        )

        return AirObject(
            scenario_bucket=ScenarioBucket.TRANSIENT_PHENOMENA,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=TruthAffiliation.NEUTRAL,
            cooperation_status=CooperationStatus.SILENT,
        )

    @staticmethod
    def create_routed_object(
        scenario_bucket: ScenarioBucket,
        platform_class: PlatformClass,
        mission_profile: MissionProfile,
        truth_affiliation: TruthAffiliation,
        cooperation_status: CooperationStatus,
        route: Route,
        callsign: Optional[str] = None,
    ) -> Flight:
        return Flight(
            scenario_bucket=scenario_bucket,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=truth_affiliation,
            cooperation_status=cooperation_status,
            route=route,
            callsign=callsign,
        )

    @staticmethod
    def sample_object_position(
        area: AreaConfig,
        platform_class: PlatformClass,
    ) -> tuple[float, float, float, float, float]:
        return (
            random.uniform(area.min_lat, area.max_lat),
            random.uniform(area.min_lon, area.max_lon),
            sample_altitude_m(platform_class),
            sample_speed_kmh(platform_class),
            random.uniform(0, 360),
        )

    @staticmethod
    def create_demo_route(platform_class: PlatformClass) -> Route:
        cruise_altitude = profile_for(platform_class).cruise_altitude_m
        origin = Waypoint(53.0, 27.0, 0.0)
        climb = Waypoint(53.4, 27.6, cruise_altitude * 0.85)
        descent = Waypoint(54.2, 28.6, cruise_altitude * 0.85)
        destination = Waypoint(54.8, 29.5, 0.0)
        return Route(origin=origin, destination=destination, waypoints=[climb, descent])

    @staticmethod
    def create_area_transit_route(area: AreaConfig, platform_class: PlatformClass) -> Route:
        origin, destination = FlightFactory._sample_boundary_pair(area)
        profile = profile_for(platform_class)

        climb_wp = FlightFactory._interpolate_waypoint(origin, destination, 0.25, profile.cruise_altitude_m * 0.8)
        cruise_wp = FlightFactory._interpolate_waypoint(origin, destination, 0.55, profile.cruise_altitude_m)
        descent_wp = FlightFactory._interpolate_waypoint(origin, destination, 0.82, max(300.0, profile.cruise_altitude_m * 0.25))

        return Route(
            origin=origin,
            destination=destination,
            waypoints=[climb_wp, cruise_wp, descent_wp],
        )

    @staticmethod
    def _sample_boundary_pair(area: AreaConfig) -> tuple[Waypoint, Waypoint]:
        edge_pairs = [
            ("west", "east"),
            ("east", "west"),
            ("north", "south"),
            ("south", "north"),
        ]
        start_edge, end_edge = random.choice(edge_pairs)
        return (
            FlightFactory._sample_boundary_waypoint(area, start_edge),
            FlightFactory._sample_boundary_waypoint(area, end_edge),
        )

    @staticmethod
    def _sample_boundary_waypoint(area: AreaConfig, edge: str, altitude: float = 0.0) -> Waypoint:
        if edge == "west":
            return Waypoint(
                lat=random.uniform(area.min_lat, area.max_lat),
                lon=area.min_lon,
                altitude=altitude,
            )
        if edge == "east":
            return Waypoint(
                lat=random.uniform(area.min_lat, area.max_lat),
                lon=area.max_lon,
                altitude=altitude,
            )
        if edge == "north":
            return Waypoint(
                lat=area.max_lat,
                lon=random.uniform(area.min_lon, area.max_lon),
                altitude=altitude,
            )
        return Waypoint(
            lat=area.min_lat,
            lon=random.uniform(area.min_lon, area.max_lon),
            altitude=altitude,
        )

    @staticmethod
    def _interpolate_waypoint(start: Waypoint, end: Waypoint, fraction: float, altitude: float) -> Waypoint:
        return Waypoint(
            lat=start.lat + (end.lat - start.lat) * fraction,
            lon=start.lon + (end.lon - start.lon) * fraction,
            altitude=altitude,
        )

    @staticmethod
    def _generate_callsign(prefix: str) -> str:
        letters = "".join(random.choices(string.ascii_uppercase, k=2))
        number = random.randint(100, 9999)
        return f"{prefix}{letters}{number}"
