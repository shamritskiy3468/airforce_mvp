from dataclasses import dataclass

from .air_object import AirObject
from .enums import FlightState
from .route import Route

@dataclass
class Flight(AirObject):
    callsign: str | None = None
    state: FlightState = FlightState.ON_GROUND
    route: Route | None = None
    current_waypoint_idx: int = 0
