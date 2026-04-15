from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from domain.enums import (
    CooperationStatus,
    DespawnReason,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    SpeedSource,
    TruthEventType,
    TruthAffiliation,
)


@dataclass(frozen=True)
class TruthEvent:
    """
    Каноническое truth-событие мира.

    event_time: симуляционное время (мир симуляции)
    ingest_time: реальное время (когда событие было создано/отправлено)
    """

    event_type: TruthEventType
    object_id: str
    scenario_bucket: ScenarioBucket
    platform_class: PlatformClass
    mission_profile: MissionProfile
    truth_affiliation: TruthAffiliation
    cooperation_status: CooperationStatus

    lat: float
    lon: float
    altitude: float
    heading: Optional[float]
    speed: Optional[float]
    speed_source: Optional[SpeedSource]

    event_time: datetime.datetime
    ingest_time: datetime.datetime
    despawn_reason: Optional[DespawnReason] = None


PositionEvent = TruthEvent
