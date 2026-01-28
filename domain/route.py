from dataclasses import dataclass, field
from typing import List

@dataclass
class Waypoint:
    lat: float
    lon: float
    altitude: float

@dataclass
class Route:
    origin: Waypoint
    destination: Waypoint
    waypoints: List[Waypoint] = field(default_factory=list)