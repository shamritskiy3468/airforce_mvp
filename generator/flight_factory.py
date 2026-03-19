import random
from typing import List, Optional
from domain.air_object import AirObject
from domain.flight import Flight
from domain.route import Route, Waypoint
from domain.enums import AirObjectType, FlightState, SpeedSource

class FlightFactory:
    """Generator for planned flights and random air objects"""

    @staticmethod
    def create_passenger_flight(origin: Waypoint, destination: Waypoint, route: Optional[Route] = None) -> Flight:
        if route is None:
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

        # Простейший пример — фиксированные аэропорты по версии Copilot :)
        airports = [
            Waypoint(52.3086, 4.7639, 0), # Schiphol
            Waypoint(51.4700, -0.4543, 0), # Heathrow
            Waypoint(40.6413, -73.7781, 0), # JFK
            Waypoint(49.0097, 2.55, 0), # Paris Charles de Gaulle, Paris
            Waypoint(52.3086, 4.7639, 0), # Amsterdam Schiphol, Amsterdam
            Waypoint(40.4936, -3.5668, 0), # Adolfo Suárez Madrid–Barajas, Madrid
            Waypoint(50.0333, 8.5706, 0), # Frankfurt Airport, Frankfurt
            Waypoint(41.2974, 2.0785, 0), # Barcelona El Prat, Barcelona
            Waypoint(48.3538, 11.7861, 0), # Munich Airport, Munich
            Waypoint(41.8003, 12.25, 0), # Rome Fiumicino, Rome
            Waypoint(48.7262, 2.3922, 0), # Paris Orly, Paris
            Waypoint(38.7742, -9.1359, 0), # Humberto Delgado Airport, Lisbon
            Waypoint(39.5517, 2.73, 0), # Palma de Mallorca Airport, Palma
            Waypoint(48.1103, 16.5636, 0), # Vienna International Airport, Vienna
            Waypoint(53.4213, -6.2701, 0), # Dublin Airport, Dublin
            Waypoint(50.9010, 4.4844, 0), # Brussels Airport, Brussels
            Waypoint(55.6180, 12.6508, 0), # Copenhagen Kastrup Airport, Copenhagen
            Waypoint(37.9364, 23.9445, 0) # Athens Eleftherios Venizelos, Athens
        ]

        for _ in range(num_passenger):
            origin, dest = random.sample(airports, 2)
            flight = FlightFactory.create_passenger_flight(origin, dest)
            scenario.append(flight)

        for _ in range(num_random):
            scenario.append(FlightFactory.create_random_air_object())

        return scenario
