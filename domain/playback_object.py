from dataclasses import dataclass

from .air_object import AirObject
from .track import Track


@dataclass
class PlaybackObject(AirObject):
    track: Track | None = None
    current_track_idx: int = 0
