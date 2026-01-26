import random
import datetime
from typing import List
from domain.air_object import AirObject
from domain.flight import Flight
from domain.route import Route, Waypoint
from domain.enums import AirObjectType, FlightState, SpeedSource

class FlightFactory:
    """Generator for planned flights and random air objects"""

    @staticmethod
    def create_passenger_flight(origin: Waypoint, destination: Waypoint) -> Flight:
        route = Route(origin=origin, destination=destination)
        flight = Flight(
            type=AirObjectType.PASSENGER_PLANE,
            state=FlightState.ON_GROUND,
            route=route
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
    def generate_scenario(num_passenger: int = 2, num_random: int = 3) -> List[AirObject]:
        """Flight scenario generator"""
        scenario = []

        # Простейший пример — фиксированные аэропорты
        airports = [
            Waypoint(52.3086, 4.7639, 0),   # Schiphol
            Waypoint(51.4700, -0.4543, 0),  # Heathrow
            Waypoint(40.6413, -73.7781, 0)  # JFK
        ]

        for _ in range(num_passenger):
            origin, dest = random.sample(airports, 2)
            flight = FlightFactory.create_passenger_flight(origin, dest)
            scenario.append(flight)

        for _ in range(num_random):
            scenario.append(FlightFactory.create_random_air_object())

        return scenario
