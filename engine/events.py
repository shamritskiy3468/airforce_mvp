from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from domain.enums import AirObjectType, SpeedSource


@dataclass(frozen=True)
class PositionEvent:
    """
    Событие обновления позиции (то, что потом можно стримить в Kafka/CH).

    event_time: симуляционное время (мир симуляции)
    ingest_time: реальное время (когда событие было создано/отправлено)
    """

    object_id: str
    object_type: AirObjectType

    lat: float
    lon: float
    altitude: float
    heading: Optional[float]
    speed: Optional[float]
    speed_source: Optional[SpeedSource]

    event_time: datetime.datetime
    ingest_time: datetime.datetime

