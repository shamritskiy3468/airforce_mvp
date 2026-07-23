ALTER TABLE airforce.truth_events_raw
ADD COLUMN IF NOT EXISTS warehouse_ingested_at Nullable(DateTime64(3, 'UTC'));

ALTER TABLE airforce.truth_events_raw
UPDATE warehouse_ingested_at = ingest_time
WHERE warehouse_ingested_at IS NULL;

ALTER TABLE airforce.truth_events_raw
MODIFY COLUMN warehouse_ingested_at DateTime64(3, 'UTC') DEFAULT now64(3);
