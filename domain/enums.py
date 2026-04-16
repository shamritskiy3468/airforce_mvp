from enum import Enum


class ScenarioBucket(Enum):
    SCHEDULED_TRAFFIC = "scheduled_traffic"
    UNSCHEDULED_TRAFFIC = "unscheduled_traffic"
    TRANSIENT_PHENOMENA = "transient_phenomena"


class PlatformClass(Enum):
    FIXED_WING_AIRCRAFT = "fixed_wing_aircraft"
    ROTARY_WING_AIRCRAFT = "rotary_wing_aircraft"
    MULTIROTOR_UAV = "multirotor_uav"
    FIXED_WING_UAV = "fixed_wing_uav"
    BALLOON = "balloon"
    BIRD_FLOCK = "bird_flock"
    WEATHER_CELL = "weather_cell"
    UNKNOWN = "unknown"


class MissionProfile(Enum):
    TRANSIT = "transit"
    PATROL = "patrol"
    LOITER = "loiter"
    TRAINING = "training"
    RECON = "recon"
    BORDER_PENETRATION = "border_penetration"
    WEATHER_DRIFT = "weather_drift"


class TruthAffiliation(Enum):
    CIVILIAN = "civilian"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    ADVERSARY = "adversary"


class CooperationStatus(Enum):
    COOPERATIVE = "cooperative"
    NON_COOPERATIVE = "non_cooperative"
    SILENT = "silent"


class FlightCategory(Enum):
    UNKNOWN = "unknown"
    PASSENGER = "passenger"
    TRAINING = "training"
    GENERAL_AVIATION = "general_aviation"
    UTILITY = "utility"


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


class TruthEventType(Enum):
    SPAWNED = "spawned"
    POSITION_UPDATED = "position_updated"
    DESPAWNED = "despawned"


class DespawnReason(Enum):
    TRANSIENT_EXPIRED = "transient_expired"
    TRANSIENT_DISTANCE_EXHAUSTED = "transient_distance_exhausted"
    TRANSIENT_LEFT_AREA = "transient_left_area"
    ROUTE_COMPLETED = "route_completed"
    PLAYBACK_COMPLETED = "playback_completed"
