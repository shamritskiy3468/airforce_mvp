from __future__ import annotations

from domain.enums import SpeedSource
from domain.playback_object import PlaybackObject
from engine.navigation.base import NavigationPolicy
from engine.navigation.math import calculate_heading, haversine_distance


class PlaybackNavigationPolicy(NavigationPolicy):
    def move(self, obj: PlaybackObject, dt_seconds: int, current_time):
        if obj.track is None or not obj.track.points:
            return

        points = obj.track.points
        first_point = points[0]
        last_point = points[-1]
        latest = obj.latest_position()

        if latest is None:
            if current_time < first_point.timestamp:
                return
            obj.current_track_idx = 0
            self._apply_point(obj, first_point, previous_point=None)
            return

        if current_time <= first_point.timestamp:
            return

        if current_time >= last_point.timestamp:
            current_idx = max(0, min(obj.current_track_idx, len(points) - 1))
            if current_idx >= len(points) - 1 and latest is not None:
                if latest.lat == last_point.lat and latest.lon == last_point.lon and latest.altitude == last_point.altitude:
                    return
            obj.current_track_idx = len(points) - 1
            self._apply_point(obj, last_point, previous_point=points[-2] if len(points) > 1 else None)
            return

        while (
            obj.current_track_idx + 1 < len(points)
            and points[obj.current_track_idx + 1].timestamp <= current_time
        ):
            obj.current_track_idx += 1

        left_idx = max(0, min(obj.current_track_idx, len(points) - 2))
        right_idx = left_idx + 1

        left = points[left_idx]
        right = points[right_idx]
        obj.current_track_idx = left_idx

        segment_seconds = (right.timestamp - left.timestamp).total_seconds()
        if segment_seconds <= 0:
            self._apply_point(obj, right, previous_point=left)
            return

        elapsed_seconds = (current_time - left.timestamp).total_seconds()
        fraction = max(0.0, min(1.0, elapsed_seconds / segment_seconds))

        lat = left.lat + (right.lat - left.lat) * fraction
        lon = left.lon + (right.lon - left.lon) * fraction
        altitude = left.altitude + (right.altitude - left.altitude) * fraction
        speed_kmh = right.speed_kmh
        if speed_kmh is None:
            speed_kmh = haversine_distance(left.lat, left.lon, right.lat, right.lon) / (segment_seconds / 3600.0)
        heading_deg = right.heading_deg
        if heading_deg is None:
            heading_deg = calculate_heading(left.lat, left.lon, right.lat, right.lon)

        if latest is not None:
            if latest.lat == lat and latest.lon == lon and latest.altitude == altitude:
                return

        obj.update_position(
            lat=lat,
            lon=lon,
            altitude=altitude,
            speed=speed_kmh,
            speed_source=SpeedSource.CALCULATED,
            heading=heading_deg,
            timestamp=current_time,
        )

    def _apply_point(self, obj: PlaybackObject, point, previous_point) -> None:
        heading_deg = point.heading_deg
        if heading_deg is None and previous_point is not None:
            heading_deg = calculate_heading(
                previous_point.lat,
                previous_point.lon,
                point.lat,
                point.lon,
            )

        speed_kmh = point.speed_kmh
        if speed_kmh is None and previous_point is not None:
            segment_seconds = (point.timestamp - previous_point.timestamp).total_seconds()
            if segment_seconds > 0:
                speed_kmh = haversine_distance(
                    previous_point.lat,
                    previous_point.lon,
                    point.lat,
                    point.lon,
                ) / (segment_seconds / 3600.0)

        obj.update_position(
            lat=point.lat,
            lon=point.lon,
            altitude=point.altitude,
            speed=speed_kmh,
            speed_source=SpeedSource.CALCULATED,
            heading=heading_deg,
            timestamp=point.timestamp,
        )
