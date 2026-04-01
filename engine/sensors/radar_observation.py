# engine/sensors/radar_observation.py

from dataclasses import dataclass
import datetime


@dataclass
class RadarObservation:
    radar_id: str
    object_id: str | None  # иногда можно сделать None (неопознанный объект)

    timestamp: datetime.datetime

    lat: float
    lon: float
    altitude: float

    # ошибки измерения
    lat_error: float
    lon_error: float
    altitude_error: float