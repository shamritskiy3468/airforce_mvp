from dataclasses import dataclass

from .air_object import AirObject
from .enums import FlightCategory, FlightState
from .route import Route

@dataclass
class Flight(AirObject):
    callsign: str | None = None
    flight_category: FlightCategory = FlightCategory.UNKNOWN
    origin_label: str | None = None
    destination_label: str | None = None
    state: FlightState = FlightState.ON_GROUND
    route: Route | None = None
    current_waypoint_idx: int = 0
