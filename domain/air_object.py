import datetime
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from .enums import AirObjectType, SpeedSource
from .kinematics import KinematicsProfile, profile_for

@dataclass
class Position:
    lat: float
    lon: float
    altitude: float
    heading: Optional[float] = None
    speed: Optional[float] = None
    speed_source: Optional[SpeedSource] = None
    timestamp: Optional[datetime.datetime] = None

@dataclass
class AirObject:
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: AirObjectType = AirObjectType.UNKNOWN
    kinematics: Optional[KinematicsProfile] = None
    positions: List[Position] = field(default_factory=list)
    max_history: int = 300

    def __post_init__(self):
        if self.kinematics is None:
            self.kinematics = profile_for(self.type)

    def update_position(self, lat: float, lon: float, altitude: float,
                        heading: Optional[float] = None,
                        speed: Optional[float] = None,
                        speed_source: Optional[SpeedSource] = None,
                        timestamp: Optional[datetime.datetime] = None):
        pos = Position(lat, lon, altitude, heading, speed, speed_source, timestamp)
        self.positions.append(pos)
        if len(self.positions) > self.max_history:
            self.positions.pop(0)

    def latest_position(self) -> Optional[Position]:
        if self.positions:
            return self.positions[-1]
        return None
    
