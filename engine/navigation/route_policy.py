from domain.flight import Flight
from domain.enums import SpeedSource, FlightState
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
            # Если дошли до конца маршрута — считаем, что самолёт приземлился.
            obj.state = FlightState.ON_GROUND
            return

        # Если начали движение по маршруту — самолёт уже не "на земле".
        # Детальную модель TAKEOFF/CLIMB/DESCENT можно добавить позже.
        if obj.state == FlightState.ON_GROUND and obj.current_waypoint_idx == 0:
            obj.state = FlightState.CRUISE

        last_pos = obj.positions[-1]

        speed = last_pos.speed or 800  # почему-то 800 км/ч для всех самолётов, можно улучшить
        remaining_km = speed * (dt_seconds / 3600)

        cur_lat, cur_lon, cur_alt = last_pos.lat, last_pos.lon, last_pos.altitude

        # Важно: CSV маршруты могут содержать очень плотные точки (тысячи).
        # Поэтому за один тик мы можем "проскочить" сразу несколько waypoint'ов,
        # пока хватает remaining_km.
        while remaining_km > 0 and obj.current_waypoint_idx < len(waypoints):
            target = waypoints[obj.current_waypoint_idx]
            dist_to_target = haversine_distance(
                cur_lat,
                cur_lon,
                target.lat,
                target.lon,
            )

            # Если можем долететь до текущего waypoint в рамках remaining_km —
            # "съедаем" waypoint и идём дальше.
            if dist_to_target <= remaining_km:
                cur_lat, cur_lon = target.lat, target.lon
                remaining_km -= dist_to_target
                obj.current_waypoint_idx += 1

                if obj.current_waypoint_idx >= len(waypoints):
                    # Долетели до destination в этом же тике.
                    obj.state = FlightState.ON_GROUND
                    cur_alt = 0.0
                    break
                continue

            # Иначе летим частично в сторону target и заканчиваем тик.
            heading = calculate_heading(
                cur_lat,
                cur_lon,
                target.lat,
                target.lon,
            )
            # Переводим remaining_km обратно в секунды того же тика:
            # distance_km = speed_kmh * dt/3600  -> dt = distance_km * 3600 / speed
            dt_partial_seconds = int(max(1.0, remaining_km * 3600 / speed))
            cur_lat, cur_lon = move_on_plane(
                cur_lat,
                cur_lon,
                speed,
                heading,
                dt_partial_seconds,
            )
            remaining_km = 0

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

    # Примечание: движение по плоскости вынесено в engine.navigation.math.move_on_plane
