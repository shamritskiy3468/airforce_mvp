# Airspace Replay

Local replay UI over `airforce.truth_events_raw` in ClickHouse.

Run:

```bash
python3 apps/airspace_replay/server.py
```

Open:

```text
http://127.0.0.1:8090
```

The app reads historical truth events from ClickHouse, filters them by `run_id` and event-time window, and replays object movement on a map.

Default ClickHouse connection:

```text
url=http://localhost:8123
database=airforce
table=airforce.truth_events_raw
user=airforce
password=airforce_pass
```

Override example:

```bash
python3 apps/airspace_replay/server.py \
  --clickhouse-url http://localhost:8123 \
  --clickhouse-database airforce \
  --clickhouse-table airforce.truth_events_raw \
  --clickhouse-user airforce \
  --clickhouse-password airforce_pass
```
