# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Navigation (read before scanning files)

Before opening any source files, read these in order:
1. `AGENT_CONTEXT.md` — task → files lookup table, key invariants, graphify commands
2. `graph-memory/SNAPSHOT.md` — current maturity stage, WIP areas
3. `graph-memory/graph.md` — compressed architectural memory (source of truth)

Module cheat-sheets: `graph-memory/modules/{domain,engine,generator,ingestors,apps,infra}.md`

Do not recursive-grep the repo. Use `graphify query "<question>"` for code-search questions.

---

## Commands

### Infrastructure
```bash
# Start full local stack (Kafka, ZooKeeper, Schema Registry, ClickHouse, Grafana, Kafka UI)
docker compose -f infrastructure/kafka/docker-compose.yml up -d

# Spark + MinIO (lake profile — not mature yet)
docker compose -f infrastructure/kafka/docker-compose.yml --profile lake up -d
```

### Simulator
```bash
# Local debug run (no Kafka needed)
python main.py --profile debug --sink console

# Avro Kafka run (infrastructure must be running)
python main.py --profile debug --sink kafka-avro

# Infinite realtime stream
python main.py --profile stream --sink kafka-avro --infinite

# Throughput benchmark (null sink, no realtime pacing)
python benchmark.py --profile load --sink null
```

### Generator cluster (3 shards, shared run_id)
```bash
bash scripts/run_generator_cluster.sh
bash scripts/stop_generator_cluster.sh
# Logs: output/cluster_pids/gen-N.log
```

### Ingestor (Kafka → ClickHouse)
```bash
bash scripts/run_ingestor.sh

# Manual equivalent
python ingestors/truth_raw_ingestor.py \
  --bootstrap-servers localhost:9094 \
  --topic airforce.truth.raw.avro.v1 \
  --message-format avro \
  --schema-registry-url http://localhost:8081 \
  --clickhouse-url http://localhost:8123 \
  --clickhouse-user airforce \
  --clickhouse-password airforce_pass
```

### End-to-end smoke test
```bash
# Requires: docker compose up, ingestor running in separate terminal
bash scripts/smoke_pipeline.sh
```

### Data utilities
```bash
# Convert CSV to route or track for manual scenarios
python helpers/csv2route.py
python helpers/csv2track.py
```

### Environment variables (Kafka/ClickHouse overrides)
| Variable | Default |
|---|---|
| `SIM_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |
| `SIM_KAFKA_TOPIC` | `airforce.truth.raw.avro.v1` |
| `SIM_SCHEMA_REGISTRY_URL` | `http://localhost:8081` |
| `SIM_AVRO_SCHEMA_PATH` | `schemas/avro/truth_event_v1.avsc` |

---

## Architecture

```
FlightFactory / ScenarioLoader
        ↓
SimulationEngine  (tick loop → TruthEvent)
        ↓
Sink: json | console | kafka | kafka-avro | null
        ↓
Kafka topic (JSON: airforce.truth.raw.v1 | Avro: airforce.truth.raw.avro.v1)
        ↓
truth_raw_ingestor  →  ClickHouse (airforce.truth_events_raw)
        ↓
Grafana dashboards / apps/airspace_replay map UI
```

**`TruthEvent` (`engine/events.py`, schema `truth_event_v1`) is the sole downstream contract.** Every schema change flows through: `events.py` → `sinks.py` → `ingestors/truth_raw_ingestor.py` → ClickHouse migration → Avro `.avsc`.

### Key modules

| Module | Responsibility |
|---|---|
| `domain/` | Core model: `AirObject`, `Flight`, `PlaybackObject`, `Route`, `Track`, enums, kinematics. No engine or ingestor imports. |
| `generator/` | `FlightFactory` auto-generates scheduled/unscheduled traffic from airport pairs and random objects |
| `engine/` | `SimulationEngine` (orchestrator), `TruthEvent`, sinks, navigation policies, runtime loops |
| `ingestors/` | Kafka consumer with manual commits → ClickHouse batch insert → DLQ for malformed payloads |
| `configs/` | `profiles.py` (launch profiles), `regions.py` (Europe + CIS bounding box) |
| `helpers/` | Sink factory, scenario loading, CSV import utilities |
| `apps/airspace_replay/` | Flask server replaying historical events from ClickHouse on a Leaflet map |

### Navigation policies (assigned in `main.py`)
- `PlaybackObject` with track → `PlaybackNavigationPolicy`
- `Flight` with route → `RouteNavigationPolicy`
- Everything else → `RandomNavigationPolicy`

### Infrastructure ports
| Service | Port |
|---|---|
| Kafka (external) | 9094 |
| Schema Registry | 8081 |
| Kafka UI | 8080 |
| ClickHouse HTTP | 8123 |
| Grafana | 3000 |

---

## Where to change things

| Task | Files |
|---|---|
| Truth schema / event fields | `engine/events.py`, `engine/sinks.py`, `ingestors/truth_raw_ingestor.py`, new CH migration |
| Avro schema | `schemas/avro/truth_event_v1.avsc`, `engine/sinks.py` (`KafkaAvroSink`), ingestor |
| World generation | `generator/flight_factory.py`, `generator/airports_catalog.py` |
| Movement / navigation | `engine/navigation/*`, `domain/kinematics.py` |
| Lifecycle / despawn | `engine/engine.py`, `engine/spawner.py`, `engine/config.py` |
| CLI / startup | `main.py`, `configs/profiles.py` |
| Sink selection / env vars | `helpers/helpers.py`, `engine/sinks.py` |
| ClickHouse marts | `migrations/clickhouse/002_create_marts.sql` |
| Infra / topics | `infrastructure/kafka/docker-compose.yml` |
| Map replay UI | `apps/airspace_replay/server.py` |

---

## Critical invariants

- `SimulationEngine` is the sole authority for `run_id`, `current_time`, and lifecycle event emission.
- Scenario merge and `activation_time` spreading happen in `main.py`, not inside the engine.
- `tick_seconds` = simulation fidelity (path resolution); `time_scale` = realtime pacing multiplier. Increase `time_scale` to accelerate without degrading path quality; increasing `tick_seconds` makes movement coarser.
- JSON and Avro **must not** share a Kafka topic.
- Ingestor commits offsets only after a successful ClickHouse insert. DLQ (`airforce.truth.dlq.v1`) is for malformed payloads only — not infrastructure failures.
- `--store-dots` requires `--sink json`.
- `domain/` must not import from `engine/` or `ingestors/`.

---

## After code changes

1. Update affected sections in `graph-memory/graph.md` (keep it compressed — rules and invariants, not prose).
2. Run `graphify update .` to refresh `graph-memory/graph.json` and `graphify-out/`.
