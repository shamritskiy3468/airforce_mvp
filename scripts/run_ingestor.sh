#!/usr/bin/env bash
# Consume truth events from the Avro Kafka topic into ClickHouse.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec python ingestors/truth_raw_ingestor.py \
  --bootstrap-servers "${KAFKA_BOOTSTRAP_SERVERS:-localhost:9094}" \
  --topic "${KAFKA_TOPIC:-airforce.truth.raw.avro.v1}" \
  --group-id "${KAFKA_GROUP_ID:-airforce-truth-raw-ingestor-avro-v1}" \
  --message-format avro \
  --schema-registry-url "${SCHEMA_REGISTRY_URL:-http://localhost:8081}" \
  --clickhouse-url "${CLICKHOUSE_URL:-http://localhost:8123}" \
  --clickhouse-database "${CLICKHOUSE_DATABASE:-airforce}" \
  --clickhouse-table "${CLICKHOUSE_TABLE:-truth_events_raw}" \
  --clickhouse-user "${CLICKHOUSE_USER:-airforce}" \
  --clickhouse-password "${CLICKHOUSE_PASSWORD:-airforce_pass}"
