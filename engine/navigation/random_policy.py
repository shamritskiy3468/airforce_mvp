import random
from domain.enums import SpeedSource
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import move_on_plane


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

        new_lat, new_lon = move_on_plane(
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
