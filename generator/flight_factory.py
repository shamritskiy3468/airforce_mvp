from dataclasses import dataclass
import math
import random
import string
from typing import List, Optional

from domain.air_object import AirObject
from domain.enums import (
    CooperationStatus,
    FlightCategory,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    TruthAffiliation,
)
from domain.flight import Flight
from domain.kinematics import profile_for, sample_altitude_m, sample_speed_kmh
from domain.route import Route, Waypoint
from engine.config import AreaConfig
from engine.navigation.math import haversine_distance


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    lat: float
    lon: float


AIRPORTS: list[Airport] = [
    Airport(code="MSQ", name="Minsk National", lat=53.8825, lon=28.0307),
    Airport(code="GME", name="Gomel", lat=52.5270, lon=31.0167),
    Airport(code="GNA", name="Grodno", lat=53.6020, lon=24.0538),
    Airport(code="BQT", name="Brest", lat=52.1083, lon=23.8981),
    Airport(code="VTB", name="Vitebsk", lat=55.1265, lon=30.3496),
    Airport(code="MVQ", name="Mogilev", lat=53.9549, lon=30.0951),
    Airport(code="VNO", name="Vilnius", lat=54.6341, lon=25.2858),
    Airport(code="KUN", name="Kaunas", lat=54.9639, lon=24.0848),
    Airport(code="PLQ", name="Palanga", lat=55.9732, lon=21.0939),
    Airport(code="RIX", name="Riga", lat=56.9236, lon=23.9711),
]


class FlightFactory:
    """Scenario generator for scheduled traffic, unscheduled traffic, and transient phenomena."""

    @staticmethod
    def generate_scenario(scheduled_traffic: int = 2, unscheduled_traffic: int = 3, transient_phenomena: int = 0, area: Optional[AreaConfig] = None) -> List[AirObject]:
        scenario = []

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

        if (
            platform_class == PlatformClass.FIXED_WING_AIRCRAFT
            and mission_profile == MissionProfile.TRANSIT
            and random.random() < 0.75
        ):
            passenger = FlightFactory.create_scheduled_passenger_flight(area)
            if passenger is not None:
                return passenger

        route = (
            FlightFactory.create_area_transit_route(area, platform_class)
            if area
            else FlightFactory.create_demo_route(platform_class)
        )
        return FlightFactory.create_routed_object(
            scenario_bucket=ScenarioBucket.SCHEDULED_TRAFFIC,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=random.choice([TruthAffiliation.CIVILIAN, TruthAffiliation.FRIENDLY]),
            cooperation_status=CooperationStatus.COOPERATIVE,
            route=route,
            callsign=FlightFactory._generate_callsign(prefix="ST"),
            flight_category=(
                FlightCategory.TRAINING
                if mission_profile == MissionProfile.TRAINING
                else FlightCategory.UTILITY
            ),
        )

    @staticmethod
    def create_scheduled_passenger_flight(area: Optional[AreaConfig]) -> Flight | None:
        airport_pair = FlightFactory._sample_airport_pair(area)
        if airport_pair is None:
            return None

        origin_airport, destination_airport = airport_pair
        route = FlightFactory.create_airport_route(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            platform_class=PlatformClass.FIXED_WING_AIRCRAFT,
        )
        return FlightFactory.create_routed_object(
            scenario_bucket=ScenarioBucket.SCHEDULED_TRAFFIC,
            platform_class=PlatformClass.FIXED_WING_AIRCRAFT,
            mission_profile=MissionProfile.TRANSIT,
            truth_affiliation=TruthAffiliation.CIVILIAN,
            cooperation_status=CooperationStatus.COOPERATIVE,
            route=route,
            callsign=FlightFactory._generate_passenger_callsign(),
            flight_category=FlightCategory.PASSENGER,
            origin_label=origin_airport.code,
            destination_label=destination_airport.code,
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
        flight_category: FlightCategory = FlightCategory.UNKNOWN,
        origin_label: str | None = None,
        destination_label: str | None = None,
    ) -> Flight:
        return Flight(
            scenario_bucket=scenario_bucket,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=truth_affiliation,
            cooperation_status=cooperation_status,
            route=route,
            callsign=callsign,
            flight_category=flight_category,
            origin_label=origin_label,
            destination_label=destination_label,
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
        return FlightFactory._build_curved_route(
            origin=origin,
            destination=destination,
            platform_class=platform_class,
            force_curve=False,
        )

    @staticmethod
    def create_airport_route(
        origin_airport: Airport,
        destination_airport: Airport,
        platform_class: PlatformClass,
    ) -> Route:
        return FlightFactory._build_curved_route(
            origin=Waypoint(origin_airport.lat, origin_airport.lon, 0.0),
            destination=Waypoint(destination_airport.lat, destination_airport.lon, 0.0),
            platform_class=platform_class,
            force_curve=True,
        )

    @staticmethod
    def _build_curved_route(
        origin: Waypoint,
        destination: Waypoint,
        platform_class: PlatformClass,
        force_curve: bool,
    ) -> Route:
        profile = profile_for(platform_class)
        distance_km = haversine_distance(origin.lat, origin.lon, destination.lat, destination.lon)

        if distance_km < 120.0:
            fractions = [0.32, 0.68]
            offset_base_km = random.uniform(6.0, 18.0)
        elif distance_km < 260.0:
            fractions = [0.22, 0.52, 0.80]
            offset_base_km = random.uniform(12.0, 35.0)
        else:
            fractions = [0.18, 0.40, 0.63, 0.84]
            offset_base_km = random.uniform(20.0, min(90.0, distance_km * 0.12))

        if force_curve and distance_km >= 180.0:
            offset_base_km = max(offset_base_km, min(110.0, distance_km * 0.10))

        if not force_curve and distance_km < 90.0:
            offset_base_km *= 0.5

        bend_sign = random.choice([-1.0, 1.0])
        waypoints: list[Waypoint] = []
        for idx, fraction in enumerate(fractions):
            altitude = FlightFactory._route_altitude_for_fraction(
                fraction=fraction,
                cruise_altitude_m=profile.cruise_altitude_m,
            )
            intensity = FlightFactory._offset_intensity(idx=idx, total=len(fractions))
            lateral_km = offset_base_km * intensity * bend_sign
            if not force_curve and abs(lateral_km) < 4.0:
                lateral_km = 0.0
            waypoints.append(
                FlightFactory._offset_interpolated_waypoint(
                    start=origin,
                    end=destination,
                    fraction=fraction,
                    altitude=altitude,
                    lateral_offset_km=lateral_km,
                )
            )

        return Route(origin=origin, destination=destination, waypoints=waypoints)

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
    def _offset_interpolated_waypoint(
        start: Waypoint,
        end: Waypoint,
        fraction: float,
        altitude: float,
        lateral_offset_km: float,
    ) -> Waypoint:
        base = FlightFactory._interpolate_waypoint(start, end, fraction, altitude)
        if lateral_offset_km == 0.0:
            return base

        lat_delta = end.lat - start.lat
        lon_delta = end.lon - start.lon
        norm = (lat_delta ** 2 + lon_delta ** 2) ** 0.5
        if norm == 0:
            return base

        perp_lat = -lon_delta / norm
        perp_lon = lat_delta / norm
        lat_offset_deg = (lateral_offset_km / 111.0) * perp_lat
        lon_scale = max(0.2, abs(math.cos(math.radians(base.lat))))
        lon_offset_deg = (lateral_offset_km / (111.0 * lon_scale)) * perp_lon
        return Waypoint(
            lat=base.lat + lat_offset_deg,
            lon=base.lon + lon_offset_deg,
            altitude=altitude,
        )

    @staticmethod
    def _offset_intensity(idx: int, total: int) -> float:
        if total == 1:
            return 1.0
        center = (total - 1) / 2
        distance_from_center = abs(idx - center)
        max_distance = max(1.0, center)
        return max(0.25, 1.0 - 0.55 * (distance_from_center / max_distance))

    @staticmethod
    def _route_altitude_for_fraction(fraction: float, cruise_altitude_m: float) -> float:
        if fraction <= 0.25:
            return cruise_altitude_m * 0.7
        if fraction >= 0.8:
            return max(500.0, cruise_altitude_m * 0.3)
        return cruise_altitude_m

    @staticmethod
    def _sample_airport_pair(area: Optional[AreaConfig]) -> tuple[Airport, Airport] | None:
        airports = AIRPORTS
        if area is not None:
            airports = [
                airport
                for airport in AIRPORTS
                if area.contains(airport.lat, airport.lon)
            ]
        if len(airports) < 2:
            return None

        origin, destination = random.sample(airports, 2)
        return origin, destination

    @staticmethod
    def _generate_callsign(prefix: str) -> str:
        letters = "".join(random.choices(string.ascii_uppercase, k=2))
        number = random.randint(100, 9999)
        return f"{prefix}{letters}{number}"

    @staticmethod
    def _generate_passenger_callsign() -> str:
        airline = random.choice(["B2", "BT", "LO", "LH", "W6", "FR"])
        return f"{airline}{random.randint(100, 9999)}"
