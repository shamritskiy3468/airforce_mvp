-- Gold-layer marts: raw -> marts (no staging, no dedup).
-- Apply after 001_create_truth_events_raw.sql and clickhouse-init.

CREATE VIEW IF NOT EXISTS airforce.mart_object_sessions AS
SELECT
    run_id,
    object_id,

    -- lifecycle
    minIf(event_time, event_type = 'spawned') AS spawned_at,
    maxIf(event_time, event_type = 'despawned') AS despawned_at,
    dateDiff(
        'second',
        minIf(event_time, event_type = 'spawned'),
        maxIf(event_time, event_type = 'despawned')
    ) AS session_duration_sec,
    countIf(event_type = 'position_updated') AS position_update_count,

    -- taxonomy (from spawn event)
    argMinIf(scenario_bucket, event_time, event_type = 'spawned') AS scenario_bucket,
    argMinIf(platform_class, event_time, event_type = 'spawned') AS platform_class,
    argMinIf(mission_profile, event_time, event_type = 'spawned') AS mission_profile,
    argMinIf(truth_affiliation, event_time, event_type = 'spawned') AS truth_affiliation,
    argMinIf(cooperation_status, event_time, event_type = 'spawned') AS cooperation_status,

    -- flight metadata (from spawn)
    argMinIf(callsign, event_time, event_type = 'spawned') AS callsign,
    argMinIf(flight_category, event_time, event_type = 'spawned') AS flight_category,
    argMinIf(origin_label, event_time, event_type = 'spawned') AS origin_label,
    argMinIf(destination_label, event_time, event_type = 'spawned') AS destination_label,

    -- geometry
    argMinIf(lat, event_time, event_type = 'spawned') AS spawn_lat,
    argMinIf(lon, event_time, event_type = 'spawned') AS spawn_lon,
    argMinIf(altitude, event_time, event_type = 'spawned') AS spawn_altitude,
    argMaxIf(lat, event_time, event_type = 'despawned') AS despawn_lat,
    argMaxIf(lon, event_time, event_type = 'despawned') AS despawn_lon,
    argMaxIf(altitude, event_time, event_type = 'despawned') AS despawn_altitude,
    argMaxIf(despawn_reason, event_time, event_type = 'despawned') AS despawn_reason,

    -- pipeline metadata
    min(ingest_time) AS first_ingest_time,
    max(ingest_time) AS last_ingest_time
FROM airforce.truth_events_raw
GROUP BY
    run_id,
    object_id;


CREATE VIEW IF NOT EXISTS airforce.mart_hourly_traffic AS
SELECT
    toStartOfHour(event_time) AS hour_utc,
    run_id,
    scenario_bucket,
    platform_class,
    truth_affiliation,

    countIf(event_type = 'spawned') AS spawns,
    countIf(event_type = 'despawned') AS despawns,
    countIf(event_type = 'position_updated') AS position_updates,

    -- objects that emitted at least one position update in this hour
    uniqExactIf(object_id, event_type = 'position_updated') AS objects_with_updates,

    -- objects that appeared (spawn) in this hour
    uniqExactIf(object_id, event_type = 'spawned') AS objects_spawned,

    min(event_time) AS first_event_time,
    max(event_time) AS last_event_time
FROM airforce.truth_events_raw
GROUP BY
    hour_utc,
    run_id,
    scenario_bucket,
    platform_class,
    truth_affiliation;
