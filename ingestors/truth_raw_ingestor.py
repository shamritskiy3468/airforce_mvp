from __future__ import annotations

import argparse
import base64
import json
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume truth events from Kafka and store them in ClickHouse."
    )
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9094",
        help="Kafka bootstrap servers, comma-separated.",
    )
    parser.add_argument(
        "--topic",
        default="airforce.truth.raw.avro.v1",
        help="Source Kafka topic with truth events.",
    )
    parser.add_argument(
        "--group-id",
        default="airforce-truth-raw-ingestor-avro-v1",
        help="Kafka consumer group id.",
    )
    parser.add_argument(
        "--dlq-topic",
        default="airforce.truth.dlq.v1",
        help="DLQ topic for malformed messages.",
    )
    parser.add_argument(
        "--message-format",
        choices=["auto", "json", "avro"],
        default="avro",
        help="Kafka value format. In auto mode, topics containing '.avro.' are treated as Avro.",
    )
    parser.add_argument(
        "--schema-registry-url",
        default="http://localhost:8081",
        help="Schema Registry URL for Avro messages.",
    )
    parser.add_argument(
        "--clickhouse-url",
        default="http://localhost:8123",
        help="Base ClickHouse HTTP URL.",
    )
    parser.add_argument(
        "--clickhouse-database",
        default="airforce",
        help="Target ClickHouse database.",
    )
    parser.add_argument(
        "--clickhouse-table",
        default="truth_events_raw",
        help="Target ClickHouse table.",
    )
    parser.add_argument(
        "--clickhouse-user",
        default="airforce",
        help="ClickHouse HTTP user.",
    )
    parser.add_argument(
        "--clickhouse-password",
        default="airforce_pass",
        help="ClickHouse HTTP password.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Max number of Kafka messages per insert batch.",
    )
    parser.add_argument(
        "--poll-timeout-ms",
        type=int,
        default=1000,
        help="Kafka poll timeout in milliseconds.",
    )
    parser.add_argument(
        "--idle-flush-seconds",
        type=float,
        default=2.0,
        help="Flush partial batch after this idle timeout.",
    )
    return parser.parse_args()


@dataclass
class NormalizedMessage:
    row: dict[str, Any]
    raw_payload: str
    kafka_topic: str
    kafka_partition: int
    kafka_offset: int


class ClickHouseWriter:
    def __init__(
        self,
        base_url: str,
        database: str,
        table: str,
        user: str,
        password: str,
    ):
        self._base_url = base_url.rstrip("/")
        self._database = database
        self._table = table
        self._auth_header = self._build_auth_header(user=user, password=password)

    @staticmethod
    def _build_auth_header(user: str, password: str) -> str:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def insert_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows).encode("utf-8")
        query = f"INSERT INTO {self._database}.{self._table} FORMAT JSONEachRow"
        req = request.Request(
            url=f"{self._base_url}/?query={parse.quote(query, safe='')}",
            data=payload,
            method="POST",
            headers={
                "Authorization": self._auth_header,
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                resp.read()
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ClickHouse HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"ClickHouse connection error: {exc.reason}") from exc

    def ensure_target_table_exists(self) -> None:
        query = f"EXISTS TABLE {self._database}.{self._table}"
        req = request.Request(
            url=f"{self._base_url}/?query={parse.quote(query, safe='')}",
            method="GET",
            headers={
                "Authorization": self._auth_header,
            },
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace").strip()
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ClickHouse HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"ClickHouse connection error: {exc.reason}") from exc

        if body != "1":
            raise RuntimeError(
                f"ClickHouse target table does not exist: {self._database}.{self._table}"
            )


class DlqProducer:
    def __init__(self, bootstrap_servers: list[str], topic: str):
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise RuntimeError(
                "truth_raw_ingestor requires dependency 'kafka-python'. Install with: pip install kafka-python"
            ) from exc

        self._topic = topic
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id="airforce-truth-raw-ingestor-dlq",
            acks="all",
            linger_ms=20,
            compression_type="gzip",
            value_serializer=lambda payload: json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8") if key is not None else None,
        )

    def publish(self, envelope: dict[str, Any], key: str | None = None) -> None:
        self._producer.send(self._topic, key=key, value=envelope)
        self._producer.flush(timeout=10.0)

    def close(self) -> None:
        self._producer.flush(timeout=10.0)
        self._producer.close()


def normalize_datetime(raw: str | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, (int, float)):
        dt = datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def build_avro_deserializer(schema_registry_url: str):
    try:
        from confluent_kafka.schema_registry import SchemaRegistryClient
        from confluent_kafka.schema_registry.avro import AvroDeserializer
    except ImportError as exc:
        raise RuntimeError(
            "Avro ingestion requires dependency 'confluent-kafka[avro]'. "
            "Install with: pip install 'confluent-kafka[avro]'"
        ) from exc

    schema_registry = SchemaRegistryClient({"url": schema_registry_url})
    return AvroDeserializer(schema_registry)


def infer_message_format(topic: str, requested_format: str) -> str:
    topic_looks_avro = ".avro." in topic or topic.endswith(".avro")
    if requested_format == "auto":
        return "avro" if topic_looks_avro else "json"
    if requested_format == "json" and topic_looks_avro:
        raise ValueError(
            f"Topic {topic!r} looks like an Avro topic, but --message-format=json was requested. "
            "Use --message-format=avro or leave the default --message-format=auto."
        )
    return requested_format


def decode_message_payload(message, message_format: str, avro_deserializer=None) -> tuple[dict[str, Any], str]:
    raw_value = message.value
    if message_format == "avro":
        if avro_deserializer is None:
            raise ValueError("avro_deserializer is required for Avro messages")
        from confluent_kafka.serialization import MessageField, SerializationContext

        payload = avro_deserializer(
            raw_value,
            SerializationContext(message.topic, MessageField.VALUE),
        )
        if payload is None:
            raise ValueError("Avro payload is empty")
        raw_payload = json.dumps(payload, ensure_ascii=False, default=str)
        return payload, raw_payload

    if isinstance(raw_value, bytes):
        raw_payload = raw_value.decode("utf-8")
    elif isinstance(raw_value, str):
        raw_payload = raw_value
    else:
        raw_payload = json.dumps(raw_value, ensure_ascii=False)

    payload = json.loads(raw_payload)
    return payload, raw_payload


def raw_payload_for_dlq(raw_value, message_format: str) -> tuple[str, str]:
    if message_format == "avro":
        if isinstance(raw_value, bytes):
            return base64.b64encode(raw_value).decode("ascii"), "base64"
        return str(raw_value), "text"
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="replace"), "utf-8"
    return str(raw_value), "text"


def normalize_message(message, message_format: str, avro_deserializer=None) -> NormalizedMessage:
    payload, raw_payload = decode_message_payload(
        message,
        message_format=message_format,
        avro_deserializer=avro_deserializer,
    )

    row = {
        "event_time": normalize_datetime(payload.get("event_time")),
        "ingest_time": normalize_datetime(payload.get("ingest_time")),
        "run_id": payload.get("run_id", ""),
        "schema_version": payload.get("schema_version", ""),
        "event_type": payload.get("event_type", ""),
        "object_id": payload.get("object_id", ""),
        "scenario_bucket": payload.get("scenario_bucket", ""),
        "platform_class": payload.get("platform_class", ""),
        "mission_profile": payload.get("mission_profile", ""),
        "truth_affiliation": payload.get("truth_affiliation", ""),
        "cooperation_status": payload.get("cooperation_status", ""),
        "callsign": payload.get("callsign"),
        "flight_category": payload.get("flight_category"),
        "origin_label": payload.get("origin_label"),
        "destination_label": payload.get("destination_label"),
        "flight_state": payload.get("flight_state"),
        "lat": payload.get("lat"),
        "lon": payload.get("lon"),
        "altitude": payload.get("altitude"),
        "heading": payload.get("heading"),
        "speed": payload.get("speed"),
        "speed_source": payload.get("speed_source"),
        "despawn_reason": payload.get("despawn_reason"),
        "kafka_topic": message.topic,
        "kafka_partition": message.partition,
        "kafka_offset": message.offset,
        "raw_payload": raw_payload,
    }

    if not row["event_time"] or not row["ingest_time"]:
        raise ValueError("event_time and ingest_time are required")
    if not row["object_id"]:
        raise ValueError("object_id is required")

    return NormalizedMessage(
        row=row,
        raw_payload=raw_payload,
        kafka_topic=message.topic,
        kafka_partition=message.partition,
        kafka_offset=message.offset,
    )


def build_dlq_envelope(message, raw_payload: str, reason: str) -> dict[str, Any]:
    return {
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "source_topic": message.topic,
        "source_partition": message.partition,
        "source_offset": message.offset,
        "key": (
            message.key.decode("utf-8", errors="replace")
            if isinstance(message.key, bytes)
            else message.key
        ),
        "reason": reason,
        "payload": raw_payload,
        "payload_encoding": "utf-8",
    }


def main() -> int:
    args = parse_args()

    try:
        from kafka import KafkaConsumer, TopicPartition
        from kafka.structs import OffsetAndMetadata
    except ImportError as exc:
        raise RuntimeError(
            "truth_raw_ingestor requires dependency 'kafka-python'. Install with: pip install kafka-python"
        ) from exc

    bootstrap_servers = [item.strip() for item in args.bootstrap_servers.split(",") if item.strip()]
    message_format = infer_message_format(args.topic, args.message_format)
    print(
        f"startup | topic={args.topic} | group_id={args.group_id} | "
        f"message_format={message_format} | bootstrap_servers={','.join(bootstrap_servers)}"
    )
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=bootstrap_servers,
        group_id=args.group_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        consumer_timeout_ms=0,
        value_deserializer=lambda payload: payload,
    )
    dlq = DlqProducer(bootstrap_servers=bootstrap_servers, topic=args.dlq_topic)
    avro_deserializer = (
        build_avro_deserializer(args.schema_registry_url)
        if message_format == "avro"
        else None
    )
    writer = ClickHouseWriter(
        base_url=args.clickhouse_url,
        database=args.clickhouse_database,
        table=args.clickhouse_table,
        user=args.clickhouse_user,
        password=args.clickhouse_password,
    )
    writer.ensure_target_table_exists()

    should_stop = False
    failed = False

    def _handle_stop(signum, frame):
        nonlocal should_stop
        should_stop = True
        print(f"signal | received={signum} | stopping=true")

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    pending_rows: list[dict[str, Any]] = []
    pending_messages = []
    last_flush_ts = time.monotonic()
    inserted_rows = 0
    dlq_rows = 0

    def build_commit_offsets(messages) -> dict[Any, Any]:
        offsets = {}
        for message in messages:
            tp = TopicPartition(message.topic, message.partition)
            offsets[tp] = OffsetAndMetadata(message.offset + 1, None, -1)
        return offsets

    def format_partition_offsets(messages) -> str:
        if not messages:
            return "-"
        latest_offsets_by_partition = {}
        for message in messages:
            latest_offsets_by_partition[message.partition] = max(
                latest_offsets_by_partition.get(message.partition, -1),
                message.offset,
            )
        return ",".join(
            f"p{partition}:{offset}"
            for partition, offset in sorted(latest_offsets_by_partition.items())
        )

    def flush_batch() -> None:
        nonlocal pending_rows, pending_messages, last_flush_ts, inserted_rows
        if not pending_rows:
            return
        partition_offsets = format_partition_offsets(pending_messages)
        writer.insert_rows(pending_rows)
        consumer.commit(offsets=build_commit_offsets(pending_messages))
        inserted_rows += len(pending_rows)
        print(
            f"flush | inserted={len(pending_rows)} | total_inserted={inserted_rows} | "
            f"partition_offsets={partition_offsets}"
        )
        pending_rows = []
        pending_messages = []
        last_flush_ts = time.monotonic()

    try:
        while not should_stop:
            polled = consumer.poll(timeout_ms=args.poll_timeout_ms, max_records=args.batch_size)
            any_message = False

            for _, messages in polled.items():
                any_message = any_message or bool(messages)
                for message in messages:
                    try:
                        normalized = normalize_message(
                            message,
                            message_format=message_format,
                            avro_deserializer=avro_deserializer,
                        )
                    except Exception as exc:
                        if pending_rows:
                            flush_batch()
                        raw_payload, payload_encoding = raw_payload_for_dlq(
                            message.value,
                            message_format=message_format,
                        )
                        envelope = build_dlq_envelope(message, raw_payload=raw_payload, reason=str(exc))
                        envelope["payload_encoding"] = payload_encoding
                        dlq.publish(envelope, key=str(message.key) if message.key is not None else None)
                        tp = TopicPartition(message.topic, message.partition)
                        consumer.commit(offsets={tp: OffsetAndMetadata(message.offset + 1, None, -1)})
                        dlq_rows += 1
                        print(
                            f"dlq | topic={message.topic} | partition={message.partition} | "
                            f"offset={message.offset} | total_dlq={dlq_rows} | reason={exc}"
                        )
                        continue

                    pending_rows.append(normalized.row)
                    pending_messages.append(message)
                    if len(pending_rows) >= args.batch_size:
                        flush_batch()

            idle_seconds = time.monotonic() - last_flush_ts
            if pending_rows and (not any_message) and idle_seconds >= args.idle_flush_seconds:
                flush_batch()
    except Exception:
        failed = True
        raise
    finally:
        if pending_rows and not failed:
            flush_batch()
        dlq.close()
        consumer.close()
        print(f"done | inserted_rows={inserted_rows} | dlq_rows={dlq_rows}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
