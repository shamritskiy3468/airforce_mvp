from domain.flight import Flight
from domain.enums import SpeedSource, FlightState
from domain.kinematics import clamp, move_altitude_towards
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import (
    haversine_distance,
    calculate_heading,
    move_on_plane,
)


class RouteNavigationPolicy(NavigationPolicy):
    def move(self, obj: Flight, dt_seconds: int, current_time):
        if not obj.route or not obj.positions:
            return

        route = obj.route
        waypoints = [route.origin] + route.waypoints + [route.destination]

        if obj.current_waypoint_idx >= len(waypoints):
            obj.state = FlightState.FINISHED
            return

        last_pos = obj.positions[-1]
        profile = obj.kinematics

        speed = self._target_speed(obj=obj, altitude=last_pos.altitude)
        speed = clamp(speed, profile.min_speed_kmh, profile.max_speed_kmh)
        remaining_km = speed * (dt_seconds / 3600)

        cur_lat, cur_lon, cur_alt = last_pos.lat, last_pos.lon, last_pos.altitude

        while remaining_km > 0 and obj.current_waypoint_idx < len(waypoints):
            target = waypoints[obj.current_waypoint_idx]
            dist_to_target = haversine_distance(
                cur_lat,
                cur_lon,
                target.lat,
                target.lon,
            )

            if dist_to_target <= remaining_km:
                cur_lat, cur_lon = target.lat, target.lon
                cur_alt = target.altitude
                remaining_km -= dist_to_target
                obj.current_waypoint_idx += 1

                if obj.current_waypoint_idx >= len(waypoints):
                    cur_alt = 0.0
                    break
                continue

            heading = calculate_heading(
                cur_lat,
                cur_lon,
                target.lat,
                target.lon,
            )
            dt_partial_seconds = int(max(1.0, remaining_km * 3600 / speed))
            cur_lat, cur_lon = move_on_plane(
                cur_lat,
                cur_lon,
                speed,
                heading,
                dt_partial_seconds,
            )
            cur_alt = move_altitude_towards(
                current_altitude_m=cur_alt,
                target_altitude_m=target.altitude,
                dt_seconds=dt_partial_seconds,
                climb_rate_mps=profile.climb_rate_mps,
                descent_rate_mps=profile.descent_rate_mps,
            )
            remaining_km = 0

        obj.state = self._derive_state(obj=obj, altitude=cur_alt, total_waypoints=len(waypoints))
        if obj.state == FlightState.FINISHED:
            speed = 0.0

        obj.update_position(
            lat=cur_lat,
            lon=cur_lon,
            altitude=cur_alt,
            speed=speed,
            speed_source=SpeedSource.CALCULATED,
            heading=calculate_heading(
                last_pos.lat,
                last_pos.lon,
                cur_lat,
                cur_lon,
            ),
            timestamp=current_time,
        )

    def _target_speed(self, obj: Flight, altitude: float) -> float:
        profile = obj.kinematics
        total_points = len([obj.route.origin] + obj.route.waypoints + [obj.route.destination])
        low_speed = max(profile.min_speed_kmh, profile.cruise_speed_kmh * 0.55)
        approach_speed = max(profile.min_speed_kmh, profile.cruise_speed_kmh * 0.45)

        if obj.current_waypoint_idx <= 1 and altitude < 300.0:
            return low_speed
        if obj.current_waypoint_idx >= total_points - 1 and altitude < 800.0:
            return approach_speed
        if altitude < profile.cruise_altitude_m * 0.7:
            return min(profile.cruise_speed_kmh * 0.75, profile.max_speed_kmh)
        return profile.cruise_speed_kmh

    def _derive_state(self, obj: Flight, altitude: float, total_waypoints: int) -> FlightState:
        if obj.current_waypoint_idx >= total_waypoints:
            return FlightState.FINISHED
        if obj.current_waypoint_idx <= 1 and altitude <= 300.0:
            return FlightState.TAKEOFF
        if obj.current_waypoint_idx >= total_waypoints - 1 and altitude <= 500.0:
            return FlightState.LANDING
        if obj.current_waypoint_idx >= total_waypoints - 2:
            return FlightState.DESCENT
        if altitude < obj.kinematics.cruise_altitude_m * 0.85:
            return FlightState.CLIMB
        return FlightState.CRUISE
