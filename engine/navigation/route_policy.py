from domain.flight import Flight
from domain.enums import SpeedSource, FlightState
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import (
    haversine_distance,
    calculate_heading,
)

class RouteNavigationPolicy(NavigationPolicy):
    def move(self, obj: Flight, dt_seconds: int, current_time):
        if not obj.route or not obj.positions:
            return

        last_pos = obj.positions[-1]
        route = obj.route
        waypoints = [route.origin] + route.waypoints + [route.destination]

        if obj.current_waypoint_idx >= len(waypoints):
            obj.state = FlightState.FINISHED
            return

        target = waypoints[obj.current_waypoint_idx]

        speed = last_pos.speed or 800
        max_distance = speed * (dt_seconds / 3600)

        distance = haversine_distance(
            last_pos.lat, last_pos.lon,
            target.lat, target.lon,
        )

        if distance <= max_distance:
            new_lat, new_lon = target.lat, target.lon
            obj.current_waypoint_idx += 1
        else:
            heading = calculate_heading(
                last_pos.lat, last_pos.lon,
                target.lat, target.lon,
            )
            new_lat, new_lon = self._move(
                last_pos.lat,
                last_pos.lon,
                speed,
                heading,
                dt_seconds,
            )

        obj.update_position(
            lat=new_lat,
            lon=new_lon,
            altitude=last_pos.altitude,
            speed=speed,
            speed_source=SpeedSource.CALCULATED,
            heading=calculate_heading(
                last_pos.lat, last_pos.lon,
                target.lat, target.lon,
            ),
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
