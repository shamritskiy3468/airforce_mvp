# Airspace Truth Simulation & Data Pipeline

## Overview

Local **truth-layer** airspace simulator and data-engineering pipeline. The system generates realistic air-object movement (flights, UAVs, transients), emits canonical `TruthEvent` logs, and streams them through Kafka into ClickHouse for analytics and map replay.

**Scope:** simulation → event log → Kafka → ClickHouse → Grafana / replay.  
**Out of scope:** radar observation layer, sensor fusion, tracking algorithms.

---

## What it does

- Simulates airspace over a configurable geographic area (Europe + CIS by default)
- Generates scheduled/unscheduled traffic and transient phenomena
- Emits lifecycle events: `spawned` → `position_updated` → `despawned`
- Publishes events to JSON/Avro Kafka topics
- Ingests into ClickHouse for SQL analytics and historical replay

---

## End-to-end flow

```
Scenario generation (FlightFactory)
        ↓
SimulationEngine (movement + lifecycle)
        ↓
TruthEvent stream
        ↓
Sink (json | console | kafka | kafka-avro)
        ↓
Kafka → truth_raw_ingestor → ClickHouse
        ↓
Grafana / airspace_replay / mart views
```

---

## Quick start

```bash
# Infrastructure
docker compose -f infrastructure/kafka/docker-compose.yml up -d

# Ingestor (separate terminal, Avro topic)
bash scripts/run_ingestor.sh

# Single simulator (Avro)
python main.py --profile debug --sink kafka-avro

# Generator cluster (Avro, 3 shards, shared run_id)
bash scripts/run_generator_cluster.sh
```

See [ROADMAP.md](ROADMAP.md) for the learning path and [PROJECT_MAP.md](PROJECT_MAP.md) for architecture details.

---

## Profiles

| Profile | Use |
|---------|-----|
| `debug` | Small local test |
| `realtime_demo` | Paced human-observable run |
| `load` | Throughput benchmark |
| `stream` | Infinite realtime Kafka stream |
| `stream_shard` | Smaller world per process — for generator clusters |
