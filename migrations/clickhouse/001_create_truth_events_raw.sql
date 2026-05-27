CREATE DATABASE IF NOT EXISTS airforce;
CREATE TABLE IF NOT EXISTS airforce.truth_events_raw
(
    event_time DateTime64(3, 'UTC') CODEC(DoubleDelta, ZSTD(1)),
    ingest_time DateTime64(3, 'UTC') CODEC(DoubleDelta, ZSTD(1)),
    event_date Date MATERIALIZED toDate(event_time),

    run_id String CODEC(ZSTD(1)),
    schema_version LowCardinality(String),

    event_type LowCardinality(String),
    object_id String CODEC(ZSTD(1)),

    scenario_bucket LowCardinality(String),
    platform_class LowCardinality(String),
    mission_profile LowCardinality(String),
    truth_affiliation LowCardinality(String),
    cooperation_status LowCardinality(String),

    callsign Nullable(String),
    flight_category Nullable(String),
    origin_label Nullable(String),
    destination_label Nullable(String),
    flight_state Nullable(String),

    lat Float64 CODEC(Gorilla, ZSTD(1)),
    lon Float64 CODEC(Gorilla, ZSTD(1)),
    altitude Float64 CODEC(Gorilla, ZSTD(1)),
    heading Nullable(Float64) CODEC(Gorilla, ZSTD(1)),
    speed Nullable(Float64) CODEC(Gorilla, ZSTD(1)),
    speed_source Nullable(String),
    despawn_reason Nullable(String),

    kafka_topic LowCardinality(String) DEFAULT '',
    kafka_partition UInt16 DEFAULT 0,
    kafka_offset UInt64 DEFAULT 0,

    raw_payload String DEFAULT '' CODEC(ZSTD(3))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (run_id, event_time, object_id, event_type)
SETTINGS index_granularity = 8192;