from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .events import TruthEvent


class EventSink(ABC):
    @abstractmethod
    def publish(self, events: Iterable[TruthEvent]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return


def truth_event_to_dict(e: TruthEvent) -> dict:
    d = asdict(e)
    d["event_type"] = e.event_type.value
    d["scenario_bucket"] = e.scenario_bucket.value
    d["platform_class"] = e.platform_class.value
    d["mission_profile"] = e.mission_profile.value
    d["truth_affiliation"] = e.truth_affiliation.value
    d["cooperation_status"] = e.cooperation_status.value
    d["flight_category"] = e.flight_category.value if e.flight_category else None
    d["flight_state"] = e.flight_state.value if e.flight_state else None
    d["speed_source"] = e.speed_source.value if e.speed_source else None
    d["despawn_reason"] = e.despawn_reason.value if e.despawn_reason else None
    d["event_time"] = e.event_time.isoformat()
    d["ingest_time"] = e.ingest_time.isoformat()
    return d


def _datetime_to_millis(value: datetime) -> int:
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


def truth_event_to_avro_dict(e: TruthEvent) -> dict:
    d = truth_event_to_dict(e)
    d["event_time"] = _datetime_to_millis(e.event_time)
    d["ingest_time"] = _datetime_to_millis(e.ingest_time)
    return d


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


class JsonSink(EventSink):
    """
    Простой синк: пишет события в JSON файл.
    Для нагрузки важно писать батчами.
    """

    def __init__(self, path: str):
        self._path = path
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> str:
        return self._path

    def publish(self, events: Iterable[TruthEvent]) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            for e in events:
                d = truth_event_to_dict(e)
                f.write(json.dumps(d, ensure_ascii=False) + "\n")


class KafkaSink(EventSink):
    def __init__(
        self,
        bootstrap_servers: list[str],
        topic: str,
        client_id: str = "airforce-simulator",
        acks: str = "all",
        linger_ms: int = 20,
        batch_size: int = 131072,
        compression_type: str = "gzip",
    ):
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise RuntimeError(
                "Kafka sink requires dependency 'kafka-python'. Install with: pip install kafka-python"
            ) from exc

        self._topic = topic
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            acks=acks,
            linger_ms=linger_ms,
            batch_size=batch_size,
            compression_type=compression_type,
            value_serializer=lambda payload: json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8"),
        )

    def publish(self, events: Iterable[TruthEvent]) -> None:
        sent = 0
        for e in events:
            self._producer.send(
                topic=self._topic,
                key=e.object_id,
                value=truth_event_to_dict(e),
            )
            sent += 1
        if sent > 0:
            self._producer.flush(timeout=10.0)

    def close(self) -> None:
        self._producer.flush(timeout=10.0)
        self._producer.close()


class KafkaAvroSink(EventSink):
    def __init__(
        self,
        bootstrap_servers: list[str],
        topic: str,
        schema_registry_url: str,
        schema_path: str,
        client_id: str = "airforce-simulator-avro",
        acks: str = "all",
        linger_ms: int = 20,
        compression_type: str = "gzip",
    ):
        try:
            from confluent_kafka import SerializingProducer
            from confluent_kafka.schema_registry import SchemaRegistryClient
            from confluent_kafka.schema_registry.avro import AvroSerializer
            from confluent_kafka.serialization import StringSerializer
        except ImportError as exc:
            raise RuntimeError(
                "Kafka Avro sink requires dependency 'confluent-kafka[avro]'. "
                "Install with: pip install 'confluent-kafka[avro]'"
            ) from exc

        schema_str = Path(schema_path).read_text(encoding="utf-8")
        schema_registry = SchemaRegistryClient({"url": schema_registry_url})
        avro_serializer = AvroSerializer(
            schema_registry_client=schema_registry,
            schema_str=schema_str,
        )

        self._topic = topic
        self._producer = SerializingProducer(
            {
                "bootstrap.servers": ",".join(bootstrap_servers),
                "client.id": client_id,
                "acks": acks,
                "linger.ms": linger_ms,
                "compression.type": compression_type,
                "key.serializer": StringSerializer("utf_8"),
                "value.serializer": avro_serializer,
            }
        )

    def publish(self, events: Iterable[TruthEvent]) -> None:
        sent = 0
        for e in events:
            self._producer.produce(
                topic=self._topic,
                key=e.object_id,
                value=truth_event_to_avro_dict(e),
            )
            sent += 1
        if sent > 0:
            self._producer.flush(timeout=10.0)

    def close(self) -> None:
        self._producer.flush(timeout=10.0)
