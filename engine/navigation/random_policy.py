import random
from domain.enums import SpeedSource
from engine.navigation.base import NavigationPolicy


class RandomNavigationPolicy(NavigationPolicy):
    def move(self, obj, dt_seconds: int, current_time):
        if not obj.positions:
            return

        last = obj.positions[-1]

        speed = last.speed or random.uniform(80, 200)
        heading = last.heading or random.uniform(0, 360)

        # иногда меняем курс
        if random.random() < 0.2:
            heading += random.uniform(-30, 30)

        new_lat, new_lon = self._move(
            last.lat,
            last.lon,
            speed,
            heading,
            dt_seconds,
        )

        obj.update_position(
            lat=new_lat,
            lon=new_lon,
            altitude=last.altitude,
            speed=speed,
            speed_source=SpeedSource.CALCULATED,
            heading=heading % 360,
            timestamp=current_time,
        )

    def _move(self, lat, lon, speed_kmh, heading_deg, dt_seconds):
        import math

        distance_km = speed_kmh * (dt_seconds / 3600)
        heading_rad = math.radians(heading_deg)

        delta_lat = distance_km * math.cos(heading_rad) / 111
        delta_lon = distance_km * math.sin(heading_rad) / (
            111 * math.cos(math.radians(lat))
        )

        return lat + delta_lat, lon + delta_lon
