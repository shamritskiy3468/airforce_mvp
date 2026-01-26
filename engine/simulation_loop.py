import datetime
import math
from typing import List

from domain.air_object import AirObject
from domain.flight import Flight
from domain.enums import FlightState, SpeedSource, AirObjectType


class SimulationLoop:
    def __init__(
        self,
        objects: List[AirObject],
        tick_seconds: int = 5,
        start_time: datetime.datetime | None = None,
    ):
        self.objects = objects
        self.tick_seconds = tick_seconds
        self.current_time = start_time or datetime.datetime.utcnow()

    def step(self):
        """
        Один тик симуляции (один radar sweep)
        """
        for obj in self.objects:
            self._update_object(obj)

        self.current_time += datetime.timedelta(seconds=self.tick_seconds)

    def _update_object(self, obj: AirObject):
        """
        Обновляем положение одного воздушного объекта
        """
        if not obj.positions:
            return

        last_pos = obj.positions[-1]

        # если скорость неизвестна — задаём реалистичную по типу
        speed = last_pos.speed or self._default_speed(obj)

        # heading тоже может быть неизвестен
        heading = last_pos.heading or self._default_heading(obj)

        # считаем новое положение
        new_lat, new_lon = self._move(
            last_pos.lat,
            last_pos.lon,
            speed,
            heading,
            self.tick_seconds,
        )

        # высота (пока примитивно)
        new_altitude = self._update_altitude(obj, last_pos.altitude)

        obj.update_position(
            lat=new_lat,
            lon=new_lon,
            altitude=new_altitude,
            speed=speed,
            speed_source=SpeedSource.CALCULATED,
            heading=heading,
            timestamp=self.current_time,
        )

    # ----------------------------
    # helpers
    # ----------------------------

    def _move(self, lat, lon, speed_kmh, heading_deg, dt_seconds):
        """
        Простейшее перемещение по сфере (упрощённо).
        Для симуляции — достаточно.
        """
        distance_km = speed_kmh * (dt_seconds / 3600)

        heading_rad = math.radians(heading_deg)

        delta_lat = distance_km * math.cos(heading_rad) / 111
        delta_lon = distance_km * math.sin(heading_rad) / (111 * math.cos(math.radians(lat)))

        return lat + delta_lat, lon + delta_lon

    def _default_speed(self, obj: AirObject) -> float:
        """
        Реалистичные скорости по типу объекта
        """
        match obj.type:
            case AirObjectType.PASSENGER_PLANE:
                return 800
            case AirObjectType.FIGHTER:
                return 900
            case AirObjectType.HELICOPTER:
                return 250
            case AirObjectType.DRONE | AirObjectType.UAV:
                return 120
            case AirObjectType.BIRD:
                return 60
            case _:
                return 100

    def _default_heading(self, obj: AirObject) -> float:
        """
        Пока просто летим в одном направлении
        """
        return 90.0  # восток

    def _update_altitude(self, obj: AirObject, current_altitude: float) -> float:
        """
        Упрощённая логика высоты
        """
        if isinstance(obj, Flight):
            match obj.state:
                case FlightState.ON_GROUND:
                    obj.state = FlightState.TAKEOFF
                    return 0
                case FlightState.TAKEOFF | FlightState.CLIMB:
                    if current_altitude < 10_000:
                        obj.state = FlightState.CLIMB
                        return current_altitude + 500
                    else:
                        obj.state = FlightState.CRUISE
                        return current_altitude
                case FlightState.CRUISE:
                    return current_altitude
                case FlightState.DESCENT:
                    return max(0, current_altitude - 500)
                case FlightState.LANDING:
                    return 0
        return current_altitude
