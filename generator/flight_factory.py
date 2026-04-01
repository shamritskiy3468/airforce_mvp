import random
import string
from typing import List, Optional

from domain.air_object import AirObject
from domain.flight import Flight
from domain.route import Route, Waypoint
from domain.enums import AirObjectType, FlightState
from domain.kinematics import profile_for, sample_altitude_m, sample_speed_kmh
from engine.config import AreaConfig

class FlightFactory:
    """Generator for planned flights and random air objects"""

    @staticmethod
    def create_passenger_flight(origin: Waypoint, destination: Waypoint, route: Optional[Route] = None) -> Flight:
        if route is None:
            route = Route(origin=origin, destination=destination)
        airline_code = "".join(random.choices(string.ascii_uppercase, k=2))
        flight_number = random.randint(100, 9999)
        flight = Flight(
            type=AirObjectType.PASSENGER_PLANE,
            state=FlightState.ON_GROUND,
            route=route,
            callsign=f"{airline_code}{flight_number}",
        )
        return flight

    @staticmethod
    def create_random_air_object() -> AirObject:
        types = [
            AirObjectType.HELICOPTER, AirObjectType.FIGHTER, AirObjectType.DRONE,
            AirObjectType.UAV, AirObjectType.JAMMER, AirObjectType.BIRD, AirObjectType.CLOUD
        ]
        obj_type = random.choice(types)
        obj = AirObject(
            type=obj_type
        )
        return obj

    @staticmethod
    def sample_object_position(area: AreaConfig, object_type: AirObjectType) -> tuple[float, float, float, float, float]:
        return (
            random.uniform(area.min_lat, area.max_lat),
            random.uniform(area.min_lon, area.max_lon),
            sample_altitude_m(object_type),
            sample_speed_kmh(object_type),
            random.uniform(0, 360),
        )

    @staticmethod
    def generate_scenario(
        num_passenger: int = 2,
        num_random: int = 3,
        area: Optional[AreaConfig] = None,
    ) -> List[AirObject]:
        """Flight scenario generator"""
        scenario = []

        for _ in range(num_passenger):
            route = FlightFactory.create_area_transit_route(area) if area else FlightFactory.create_demo_route()
            flight = FlightFactory.create_passenger_flight(route.origin, route.destination, route=route)
            scenario.append(flight)

        for _ in range(num_random):
            scenario.append(FlightFactory.create_random_air_object())

        return scenario

    @staticmethod
    def create_demo_route() -> Route:
        origin = Waypoint(53.0, 27.0, 0.0)
        climb = Waypoint(53.4, 27.6, 9_000.0)
        descent = Waypoint(54.2, 28.6, 9_000.0)
        destination = Waypoint(54.8, 29.5, 0.0)
        return Route(origin=origin, destination=destination, waypoints=[climb, descent])

    @staticmethod
    def create_area_transit_route(area: AreaConfig) -> Route:
        origin, destination = FlightFactory._sample_boundary_pair(area)
        profile = profile_for(AirObjectType.PASSENGER_PLANE)

        climb_wp = FlightFactory._interpolate_waypoint(origin, destination, 0.25, profile.cruise_altitude_m)
        cruise_wp = FlightFactory._interpolate_waypoint(origin, destination, 0.55, profile.cruise_altitude_m)
        descent_wp = FlightFactory._interpolate_waypoint(origin, destination, 0.82, 2_500.0)

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
    def _interpolate_waypoint(
        start: Waypoint,
        end: Waypoint,
        fraction: float,
        altitude: float,
    ) -> Waypoint:
        return Waypoint(
            lat=start.lat + (end.lat - start.lat) * fraction,
            lon=start.lon + (end.lon - start.lon) * fraction,
            altitude=altitude,
        )
