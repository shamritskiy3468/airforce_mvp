#!/usr/bin/env bash
# Short end-to-end check: finite sim -> Avro Kafka -> ClickHouse row count.
# Requires: docker compose up, bash scripts/run_ingestor.sh in another terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_ID="${RUN_ID:-smoke-$(date +%Y%m%d-%H%M%S)}"
STEPS="${STEPS:-120}"
PROFILE="${PROFILE:-debug}"
SINK="${SINK:-kafka-avro}"

export SIM_KAFKA_BOOTSTRAP_SERVERS="${SIM_KAFKA_BOOTSTRAP_SERVERS:-localhost:9094}"
export SIM_KAFKA_TOPIC="${SIM_KAFKA_TOPIC:-airforce.truth.raw.avro.v1}"
export SIM_SCHEMA_REGISTRY_URL="${SIM_SCHEMA_REGISTRY_URL:-http://localhost:8081}"
export SIM_AVRO_SCHEMA_PATH="${SIM_AVRO_SCHEMA_PATH:-schemas/avro/truth_event_v1.avsc}"

echo "smoke | run_id=$RUN_ID | profile=$PROFILE | steps=$STEPS | sink=$SINK | topic=$SIM_KAFKA_TOPIC"

python main.py \
  --profile "$PROFILE" \
  --sink "$SINK" \
  --run-id "$RUN_ID" \
  --max-steps "$STEPS"

echo "smoke | waiting 5s for ingestor flush..."
sleep 5

count="$(
  curl -s "http://localhost:8123/" \
    --user airforce:airforce_pass \
    --data-binary "SELECT count() FROM airforce.truth_events_raw WHERE run_id = '${RUN_ID}' FORMAT TabSeparated"
)"

echo "smoke | clickhouse_rows=$count | run_id=$RUN_ID"

if [[ "${count:-0}" -eq 0 ]]; then
  echo "FAIL: no rows in ClickHouse."
  echo "Start ingestor: bash scripts/run_ingestor.sh"
  exit 1
fi

echo "OK: Avro pipeline delivered events to ClickHouse"
