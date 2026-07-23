# Roadmap — куда двигаться дальше

> Экспертный план обучения под **текущий** статус проекта.  
> Принцип: **сначала замкнуть один рабочий контур**, потом добавлять технологии.

---

## Где ты сейчас

**Готово и ценно:**
- Truth-layer симулятор (`SimulationEngine`, таксономия, navigation)
- Kafka sink (JSON + Avro WIP)
- Ingestor → ClickHouse + DLQ
- Replay UI (`apps/airspace_replay`)
- CH marts (views)
- Cluster flags в `main.py` (`--run-id`, `--object-id-prefix`)

**Не готово / не трогать пока:**
- Spark jobs — контейнеры есть, кода нет
- Airflow — нет

---

## Архитектурное решение (моя рекомендация)

### Один primary path на ближайшие 2–3 недели

```
N × simulator (stream_shard, sink kafka-avro)
    → Kafka topic airforce.truth.raw.avro.v1
    → truth_raw_ingestor (scripts/run_ingestor.sh)
    → ClickHouse truth_events_raw
    → Grafana + airspace_replay + mart_* views
```

**Не поднимай Spark/MinIO**, пока этот контур не работает 1+ час без сюрпризов.

Lake-стек (Spark, MinIO) — **этап 4**, не этап 1:
```bash
docker compose -f infrastructure/kafka/docker-compose.yml --profile lake up -d
```

### Что я считаю bullshit и уже поправил

| Проблема | Что сделано |
|----------|-------------|
| `scripts/` и `apps/` в `.gitignore` | убрано — код должен быть в git |
| Две миграции `002_*` | `003_add_warehouse_ingested_at.sql` |
| Ingestor default user `default` | → `airforce` / `airforce_pass` |
| Spark/MinIO всегда в compose | profile `lake` — опционально |
| Мусор `generator/Untitled` | удалён |
| Нет способа запустить кластер | `scripts/run_generator_cluster.sh` |

### Что пока не рефакторил (осознанно)

- `Helpers.create_sink()` в `helpers/helpers.py` — работает, вынесем позже
- Дублирование kafka env в sink factory — терпимо на MVP

---

## Этапы (конкретные, осязаемые)

### Этап 1 — Замкнуть streaming loop (1–2 вечера)

**Цель:** убедиться, что данные текут без ручной магии.

```bash
# 1. Infra (только core, без Spark)
docker compose -f infrastructure/kafka/docker-compose.yml up -d

# Ingestor (терминал 1)
bash scripts/run_ingestor.sh

# Smoke test (терминал 2)
bash scripts/smoke_pipeline.sh

# Кластер генераторов (терминал 2)
bash scripts/run_generator_cluster.sh

# 5. Проверки
# - Kafka UI http://localhost:8080 — lag ingestor group
# - ClickHouse: SELECT run_id, count() FROM truth_events_raw GROUP BY run_id
# - Replay http://127.0.0.1:8090 — тот же run_id
```

**Критерий «готово»:**
- [ ] 3 генератора пишут в один `run_id`
- [ ] CH растёт, DLQ пустой
- [ ] Replay показывает объекты с prefix `g1-`, `g2-`, `g3-`
- [ ] После `stop_generator_cluster.sh` ingestor догоняет lag до ~0

---

### Этап 2 — Наблюдаемость (2–3 вечера)

**Цель:** видеть систему глазами DE-инженера, не только «данные есть».

1. **Grafana dashboard** (минимум 3 панели):
   - events/sec по `ingest_time`
   - consumer lag (или proxy: max kafka_offset − rows in CH за run)
   - breakdown by `platform_class` / `truth_affiliation`

2. **Запросы к marts:**
   ```sql
   SELECT * FROM airforce.mart_hourly_traffic WHERE run_id = '...' ORDER BY hour_utc;
   SELECT * FROM airforce.mart_object_sessions WHERE run_id = '...' LIMIT 20;
   ```

3. **1-часовой soak test:**
   ```bash
   GENERATORS=3 bash scripts/run_generator_cluster.sh
   # через час — stop, проверить CH count, DLQ, replay
   ```

**Критерий «готово»:**
- [ ] Dashboard открывается без ручного SQL каждый раз
- [ ] Понимаешь, где теряются события (если теряются)

---

### Этап 3 — Avro как production format (2–4 дня)

**Цель:** Schema Registry + typed contract (навык для реального DE).

1. Переключить кластер на Avro:
   ```bash
   SINK=kafka-avro bash scripts/run_generator_cluster.sh
   python ingestors/truth_raw_ingestor.py \
     --topic airforce.truth.raw.avro.v1 --message-format avro
   ```
2. Убедиться: Schema Registry показывает `truth_event_v1`
3. JSON topic оставить для debug, **не смешивать** форматы

**Критерий «готово»:**
- [ ] Avro path = тот же row count в CH, что JSON path
- [ ] Можешь объяснить: wire format, millis timestamps, SR subject

---

### Этап 4 — Lake (Spark + MinIO) — только после этапа 3

**Цель:** batch landing, не realtime ingest.

```bash
docker compose -f infrastructure/kafka/docker-compose.yml --profile lake up -d
```

**Первый job (единственный на старте):**
- Spark batch каждые 15 мин: Kafka Avro → Parquet в `s3a://airforce-lake/bronze/truth_events/`
- Partition: `run_id`, `dt`, `hour`

**Airflow** — только orchestrator этого job + data quality check:
- count bronze vs CH за окно
- DLQ rate

**Не делай пока:** Silver/Gold в Spark, если marts в CH уже отвечают на вопросы.

---

## Что учишь на каждом этапе

| Этап | Технологии | Навык |
|------|------------|-------|
| 1 | Kafka, consumer groups, batch insert | multi-producer streaming |
| 2 | ClickHouse, Grafana, SQL marts | observability + OLAP |
| 3 | Avro, Schema Registry | schema evolution |
| 4 | Spark, MinIO, Airflow | lakehouse batch pattern |

---

## Следующее действие (прямо сейчас)

```bash
docker compose -f infrastructure/kafka/docker-compose.yml up -d
bash scripts/run_ingestor.sh &
bash scripts/smoke_pipeline.sh
bash scripts/run_generator_cluster.sh
```

Если smoke падает — чини ingestor/compose, **не добавляй Spark**.

---

## Связанные файлы

- `PROJECT_MAP.md` — карта модулей
- `graph-memory/SNAPSHOT.md` — снимок статуса для агента
- `scripts/run_generator_cluster.sh` — кластер генераторов
- `scripts/smoke_pipeline.sh` — быстрая проверка контура
