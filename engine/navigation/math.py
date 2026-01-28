import math

EARTH_RADIUS_KM = 6371


def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def calculate_heading(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)
    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def move_on_plane(lat, lon, speed_kmh, heading_deg, dt_seconds):
    """
    Упрощённое движение (плоская модель)
    """
    distance_km = speed_kmh * (dt_seconds / 3600)
    heading_rad = math.radians(heading_deg)

    delta_lat = distance_km * math.cos(heading_rad) / 111
    delta_lon = distance_km * math.sin(heading_rad) / (
        111 * math.cos(math.radians(lat))
    )

    return lat + delta_lat, lon + delta_lon
