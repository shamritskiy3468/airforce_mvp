#!/usr/bin/env bash
# Start N simulator shards into the Avro Kafka topic with a shared run_id.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GENERATORS="${GENERATORS:-3}"
PROFILE="${PROFILE:-stream_shard}"
SINK="${SINK:-kafka-avro}"
RUN_ID="${RUN_ID:-cluster-$(date +%Y%m%d-%H%M%S)}"
PID_DIR="${PID_DIR:-$ROOT/output/cluster_pids}"

export SIM_KAFKA_BOOTSTRAP_SERVERS="${SIM_KAFKA_BOOTSTRAP_SERVERS:-localhost:9094}"
export SIM_KAFKA_TOPIC="${SIM_KAFKA_TOPIC:-airforce.truth.raw.avro.v1}"
export SIM_SCHEMA_REGISTRY_URL="${SIM_SCHEMA_REGISTRY_URL:-http://localhost:8081}"
export SIM_AVRO_SCHEMA_PATH="${SIM_AVRO_SCHEMA_PATH:-schemas/avro/truth_event_v1.avsc}"

mkdir -p "$PID_DIR"

echo "cluster | run_id=$RUN_ID | generators=$GENERATORS | profile=$PROFILE | sink=$SINK"
echo "cluster | topic=$SIM_KAFKA_TOPIC | schema_registry=$SIM_SCHEMA_REGISTRY_URL"

for i in $(seq 1 "$GENERATORS"); do
  seed=$((1000 + i))
  prefix="g${i}-"
  producer_id="gen-${i}"
  log_file="$PID_DIR/${producer_id}.log"

  python main.py \
    --profile "$PROFILE" \
    --sink "$SINK" \
    --infinite \
    --run-id "$RUN_ID" \
    --seed "$seed" \
    --object-id-prefix "$prefix" \
    --producer-id "$producer_id" \
    --region-id "shard-${i}" \
    >"$log_file" 2>&1 &

  pid=$!
  echo "$pid" >"$PID_DIR/${producer_id}.pid"
  echo "started | producer_id=$producer_id | pid=$pid | prefix=$prefix | log=$log_file"
done

echo
echo "Ingestor (separate terminal):"
echo "  bash scripts/run_ingestor.sh"
echo
echo "Stop generators:"
echo "  bash scripts/stop_generator_cluster.sh"
echo
echo "Tail one log:"
echo "  tail -f $PID_DIR/gen-1.log"
