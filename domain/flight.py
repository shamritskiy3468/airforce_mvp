from dataclasses import dataclass
from .air_object import AirObject
from .route import Route
from .enums import FlightState

@dataclass
class Flight(AirObject):
    state: FlightState = FlightState.ON_GROUND
    route: Route | None = None  # для рейсовых самолётов
    # индекс текущего waypoint
    current_waypoint_idx: int = 0