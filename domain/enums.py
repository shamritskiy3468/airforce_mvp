from enum import Enum

class AirObjectType(Enum):
    PASSENGER_PLANE = "passenger_plane"
    HELICOPTER = "helicopter"
    FIGHTER = "fighter"
    DRONE = "drone"
    UAV = "uav"
    JAMMER = "jammer"
    BIRD = "bird"
    CLOUD = "cloud"
    UNKNOWN = "unknown"

class FlightState(Enum):
    ON_GROUND = "on_ground"
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    LANDING = "landing"
    FINISHED = "finished"

class SpeedSource(Enum):
    RADAR = "radar"           # скорость пришла от радара (мы ей доверяем)
    CALCULATED = "calculated" # скорость рассчитана по координатам