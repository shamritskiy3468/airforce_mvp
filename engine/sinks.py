from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Iterable, Optional

from .events import TruthEvent


class EventSink(ABC):
    @abstractmethod
    def publish(self, events: Iterable[TruthEvent]) -> None:
        raise NotImplementedError


class NullSink(EventSink):
    def publish(self, events: Iterable[TruthEvent]) -> None:
        return


class ConsoleSink(EventSink):
    def __init__(self, every_n_events: int = 1): # выводить каждые 100 событий
        self._n = max(1, every_n_events)
        self._counter = 0

    def publish(self, events: Iterable[TruthEvent]) -> None:
        for e in events:
            self._counter += 1
            if self._counter % self._n != 0:
                continue
            print(
                f"{e.event_time.isoformat()} | {e.event_type.value:<16} | "
                f"{e.platform_class.value:<20} | lat={e.lat:.4f}, lon={e.lon:.4f}, alt={e.altitude:>5.0f}"
            )


class JsonlSink(EventSink):
    """
    простой синк: пишет события в JSONL файл.
    Для нагрузки важно писать батчами.
    """

    def __init__(self, path: str):
        self._path = path

    def publish(self, events: Iterable[TruthEvent]) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            for e in events:
                d = asdict(e)
                # Enum → value для сериализации
                d["event_type"] = e.event_type.value
                d["scenario_bucket"] = e.scenario_bucket.value
                d["platform_class"] = e.platform_class.value
                d["mission_profile"] = e.mission_profile.value
                d["truth_affiliation"] = e.truth_affiliation.value
                d["cooperation_status"] = e.cooperation_status.value
                d["speed_source"] = e.speed_source.value if e.speed_source else None
                d["despawn_reason"] = e.despawn_reason.value if e.despawn_reason else None
                d["event_time"] = e.event_time.isoformat()
                d["ingest_time"] = e.ingest_time.isoformat()
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
