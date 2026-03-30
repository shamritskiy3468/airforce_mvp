import random

from domain.enums import SpeedSource
from domain.kinematics import clamp, move_altitude_towards
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import move_on_plane


class RandomNavigationPolicy(NavigationPolicy):
    def move(self, obj, dt_seconds: int, current_time):
        if not obj.positions:
            return

        last = obj.positions[-1]
        profile = obj.kinematics

        if last.speed is None:
            speed = random.uniform(profile.min_speed_kmh, profile.max_speed_kmh)
        else:
            speed = last.speed + random.uniform(-15.0, 15.0)
        speed = clamp(speed, profile.min_speed_kmh, profile.max_speed_kmh)

        heading = last.heading if last.heading is not None else random.uniform(0, 360)
        heading += random.uniform(-profile.max_turn_rate_deg, profile.max_turn_rate_deg)

        new_lat, new_lon = move_on_plane(
            last.lat,
            last.lon,
            speed,
            heading,
            dt_seconds,
        )

        target_altitude = clamp(
            profile.cruise_altitude_m + random.uniform(-250.0, 250.0),
            profile.min_altitude_m,
            profile.max_altitude_m,
        )
        new_altitude = move_altitude_towards(
            current_altitude_m=last.altitude,
            target_altitude_m=target_altitude,
            dt_seconds=dt_seconds,
            climb_rate_mps=profile.climb_rate_mps,
            descent_rate_mps=profile.descent_rate_mps,
        )

        obj.update_position(
            lat=new_lat,
            lon=new_lon,
            altitude=new_altitude,
            speed=speed,
            speed_source=SpeedSource.CALCULATED,
            heading=heading % 360,
            timestamp=current_time,
        )
