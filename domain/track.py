from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrackPoint:
    timestamp: datetime.datetime
    lat: float
    lon: float
    altitude: float
    speed_kmh: float | None = None
    heading_deg: float | None = None


@dataclass(frozen=True)
class Track:
    points: list[TrackPoint] = field(default_factory=list)

    def __post_init__(self):
        if not self.points:
            raise ValueError("Track must contain at least 1 point")
        timestamps = [point.timestamp for point in self.points]
        if timestamps != sorted(timestamps):
            raise ValueError("Track points must be sorted by timestamp")
