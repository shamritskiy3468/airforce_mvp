from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from domain.enums import (
    CooperationStatus,
    DespawnReason,
    FlightCategory,
    FlightState,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    SpeedSource,
    TruthEventType,
    TruthAffiliation,
)

TRUTH_EVENT_SCHEMA_VERSION = "truth_event_v1"


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
    callsign: Optional[str]
    flight_category: Optional[FlightCategory]
    origin_label: Optional[str]
    destination_label: Optional[str]
    flight_state: Optional[FlightState]

    lat: float
    lon: float
    altitude: float
    heading: Optional[float]
    speed: Optional[float]
    speed_source: Optional[SpeedSource]

    event_time: datetime.datetime
    ingest_time: datetime.datetime
    run_id: str
    schema_version: str
    despawn_reason: Optional[DespawnReason] = None


PositionEvent = TruthEvent
