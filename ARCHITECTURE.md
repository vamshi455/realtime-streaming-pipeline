# Deep-Dive: Streaming Architecture

This document explains the architectural decisions, medallion layer design, watermark tuning, recovery patterns, and observability instrumentation.

## Table of Contents

1. [Medallion Architecture (Bronze/Silver/Gold)](#medallion-architecture)
2. [Watermark Mechanics & Tuning](#watermark-mechanics--tuning)
3. [Version-Wins MERGE & Dedup](#version-wins-merge--dedup)
4. [Recovery Paths: Streaming vs Batch](#recovery-paths-streaming-vs-batch)
5. [Reconciliation Strategy](#reconciliation-strategy)
6. [Observability: Metrics-First Design](#observability-metrics-first-design)
7. [Edge Cases & Failure Modes](#edge-cases--failure-modes)

## Medallion Architecture

The three-layer delta medallion (Bronze/Silver/Gold) separates concerns and enables iterative refinement:

### 🔵 Bronze Layer (Raw, Append-Only)

**Purpose**: Immutable source of truth. Every raw event from Kafka preserved exactly as received.

**Characteristics**:
- Schema: minimal transformation (add `_ingest_ts`, `_kafka_offset`, `_kafka_partition`)
- Partitioning: by `_kafka_topic` (one table per Kafka topic)
- Compaction: NONE — append-only for full replay capability
- Watermark: NONE applied here; watermark is a concern of consumers, not the raw layer
- Retention: indefinite (in practice, pruned by age; local demo keeps everything)

**Why**: If something goes wrong downstream, we can always replay Bronze from any point in time. No data is lost in transformation; Bronze is the "black box" recording.

**Example queries**:
```sql
-- Full replay of a deal_id for a specific date
SELECT * FROM bronze_deals 
WHERE deal_id = 'DEAL-123' 
  AND _ingest_ts >= '2024-08-10' AND _ingest_ts < '2024-08-11'
ORDER BY _ingest_ts;

-- Inspect raw event payload (if JSON)
SELECT *, get_json_object(raw_payload, '$.counterparty') as counterparty
FROM bronze_deals WHERE deal_id = 'DEAL-123' LIMIT 1;
```

### 🟡 Silver Layer (Cleaned, Deduplicated)

**Purpose**: Single source of truth for business entities. Deduplicates via version-wins MERGE, applies watermark to catch late-arrivals.

**Characteristics**:
- Watermark: `withWatermark("event_time", "4 hours")` — covers realistic late nominations/corrections
- MERGE logic: keyed by entity ID + version/sequence fields; highest version wins
- Schema: fully structured, business-level fields (no raw payloads), strongly typed
- Partitioning: by entity key (e.g., `deal_id` mod N) for MERGE efficiency
- Retention: keyed tables, old versions not deleted (Delta time-travel enables full history)

**Why**: Medallion layer separates raw ingest (Bronze) from business-logic cleaning (Silver). By the time data reaches Silver, we've deduplicated and established "the" truth for that deal/nomination.

**MERGE on Write** (`foreachBatch`):
```python
# Pseudocode
def silver_merge_batch(batch_df, epoch_id):
    batch_df.write.format("delta") \
        .mode("merge") \
        .option("mergeSchema", "true") \
        .mergeInto("silver_deals") \
        .on("deal_id") \
        .whenMatchedAndVersionGreater("deal_version") \
            .updateAll() \
        .whenNotMatched() \
            .insertAll() \
        .execute()
```

**Why version-wins?** If an event arrives out-of-order (v3 before v2), the MERGE keeps v3 until v2 or v1 arrives later with a higher version. This prevents stale data from overwriting newer data.

**Example**: A deal amendment (v2) is sent 3 hours late but arrives *before* the initial deal (v1) due to a network hiccup. Silver MERGE preserves v2 as the current state, and ignores v1 when it eventually arrives (since v1 < v2).

### 🟢 Gold Layer (Business Aggregates)

**Purpose**: Read-optimized aggregates for real-time dashboards and analytics. Typically computed via windowed joins of Silver streams.

**Characteristics**:
- Windowing: tumbling or sliding window per `settlement_period` or business time
- Join: Silver deal legs + nominations + Silver LMP prices → aggregated positions
- Output: POSITION table (book_id, delivery_node, settlement_period, net_mw, mtm_value, as_of_datetime)
- Dual sink: (1) Delta MERGE for durable history, (2) Redis for sub-second read latency
- Retention: full Delta history for audit; Redis eviction policy (e.g., LRU) for live cache

**Why dual sink?**
- **Delta**: durable, queryable, historical (audit trail, time-travel), but slower read latency (milliseconds vs microseconds)
- **Redis**: live cache, sub-millisecond reads, but limited retention; refreshable from Gold on cache miss

**Example**:
```python
# Pseudocode
positions_df = silver_deals \
    .join(silver_legs, "deal_id") \
    .join(silver_nominations, ["deal_id", "settlement_period"]) \
    .join(silver_lmp, ["delivery_node", "settlement_period"]) \
    .groupBy("book_id", "delivery_node", "settlement_period") \
    .agg(
        sum("volume_mw") -> "net_mw",
        sum(col("volume_mw") * col("lmp")) -> "mtm_value",
        max("event_time") -> "as_of_datetime"
    ) \
    .withColumn("source_version", monotonically_increasing_id())  # for idempotency

positions_df.writeStream \
    .foreachBatch(dual_sink_gold) \
    .start()
```

## Watermark Mechanics & Tuning

A watermark is a **conceptual threshold of progress** in event time. Events arriving after the watermark is "closed" on a window are handled specially (either dropped or routed to batch recompute).

### The Tradeoff

- **Long watermark** (e.g., 4 hours): catches late nominations/corrections, but inflates state size in memory, adds latency (Spark holds windows open longer)
- **Short watermark** (e.g., 10 minutes): tight latency, small state, but misses realistic late-arrivals

### Watermark = 4 Hours

We've chosen **4 hours** for this project because:

1. **Domain knowledge**: power market nominations frequently arrive 3–4 hours late as counterparties confirm transport capacity
2. **Practical**: local Spark memory is unconstrained; 4h window over ~6 delivery nodes ≈ 100s of MB
3. **Recovery fallback**: corrections older than 4h don't fail silently; they explicitly trigger `batch_recompute` (see [Recovery Paths](#recovery-paths-streaming-vs-batch))

### Configuring Watermark

In `.env`:
```bash
WATERMARK_WINDOW_HOURS=4
```

In Spark job:
```python
df_with_watermark = df \
    .withWatermark("event_time", f"{watermark_hours} hours")
```

### What Happens When a Correction Arrives Older Than Watermark?

**Streaming path**: event is dropped (older than watermark, window already closed).

**But we don't lose it**: The correction lands in Kafka. A separate `batch_recompute` watcher detects it (via a poison-pill pattern or explicit monitoring job) and routes it to the batch path:
1. Read Bronze/Silver for the affected entity from the correction's event_time ± buffer
2. Recompute Gold rows affected by that entity
3. MERGE back into Gold

This is the **explicit recovery fallback** — addressed in the next section.

## Version-Wins MERGE & Dedup

**Idempotency requirement**: If an event is replayed or arrives twice (network hiccup), the system must not double-count.

### The Problem

If we naively append every event, a duplicate LMP tick produces two `net_mw` values, and summing them inflates position.

### The Solution: Version-Wins MERGE

Every event carries a `version` or `sequence` number. The MERGE logic keeps the **highest version** per entity key:

**MERGE predicate**:
```sql
MERGE INTO silver_deals t USING updates s
ON t.deal_id = s.deal_id
WHEN MATCHED AND s.deal_version > t.deal_version THEN UPDATE SET *
WHEN MATCHED AND s.deal_version <= t.deal_version THEN /* do nothing, keep t */
WHEN NOT MATCHED THEN INSERT *
```

**Why this works**:
- Duplicate arrives with **same version** → `s.deal_version <= t.deal_version`, do nothing
- Out-of-order arrives with **higher version** → `s.deal_version > t.deal_version`, update (this is the corrected state)
- Stale replay arrives with **lower version** → do nothing (current state is newer)

### Metrics: Dedup Tracking

```python
# In Silver job, after MERGE
duplicates_df = new_batch \
    .join(existing_df, ["deal_id"], "inner") \
    .filter(col("new_version") <= col("existing_version"))

metrics.emit(
    "events_deduped",
    duplicates_df.count(),
    tags={"topic": "deal.events"}
)
```

This metric tells you **how many duplicate events were silently filtered out**. If it's non-zero, you've got a network/producer issue worth investigating.

## Recovery Paths: Streaming vs Batch

There are two ways a correction gets reprocessed: **streaming path** (watermark catches it) and **batch path** (watermark misses it, we explicitly recompute).

### Streaming Path (Ideal, Fast)

Event arrives in Kafka **before the watermark closes** on its window.

1. Event flows through Bronze → Silver → Gold normally
2. Silver MERGE dedup catches it (version-wins or exact duplicate)
3. Gold aggregation includes the corrected value
4. Redis updated; Gold Delta updated
5. Reconciliation compares vs Postgres, heals if needed
6. **Latency**: ~30–100 ms end-to-end

### Batch Path (Fallback, Slower)

Event arrives **after watermark closes** (e.g., 5 hours after original event).

1. Event lands in Kafka, but Spark streaming doesn't process it (watermark has moved on)
2. Batch recompute job detects it (via topic lag monitoring or explicit poison-pill topic)
3. Job reads Bronze/Silver for affected entity key from `event_time - buffer` to `event_time + buffer`
4. Recomputes Gold rows for that key
5. MERGE back into Gold
6. Reconciliation observes the update
7. **Latency**: ~1–5 seconds (depends on how much backlog to recompute)

### How Batch Recompute Is Triggered

**Option 1: Automatic (via topic lag monitoring)**
```python
# In a scheduler job
lag = get_kafka_consumer_lag("nominations.events")
if lag > watermark_threshold_offset:
    affected_keys = find_affected_keys_from_lag_window()
    trigger_batch_recompute(affected_keys)
```

**Option 2: Explicit (poison-pill topic)**
```python
# Producer, when it detects old event
if event.event_time < now() - watermark:
    producer.send("recompute.trigger", {
        "entity_id": event.deal_id,
        "event_time_min": event.event_time,
        "event_time_max": now()
    })

# Batch recompute job listens to recompute.trigger, acts on each message
```

We use **Option 2** (explicit trigger) for clarity and testability.

## Reconciliation Strategy

**Goal**: Ensure streaming aggregate (Gold) stays in sync with source of truth (Postgres book-of-record).

### The Flow

```python
def reconciliation_job():
    while True:
        # 1. Query source of truth
        postgres_positions = pd.read_sql("""
            SELECT book_id, delivery_node, settlement_period, net_mw, mtm_value
            FROM position_snapshot
            WHERE updated_at >= now() - interval '10 minutes'
        """, postgres_conn)
        
        # 2. Query streaming aggregate
        gold_positions = deltalake.DeltaTable("data/delta/gold_positions") \
            .to_pandas() \
            .query('as_of_datetime >= @recent_time')
        
        # 3. Full outer join
        diff = postgres_positions.merge(
            gold_positions,
            on=["book_id", "delivery_node", "settlement_period"],
            how="outer",
            indicator=True,
            suffixes=("_postgres", "_gold")
        )
        
        # 4. Assess drift
        for row in diff.itertuples():
            mw_diff = abs(row.net_mw_postgres - row.net_mw_gold)
            pct_diff = abs(mw_diff / row.net_mw_postgres) if row.net_mw_postgres else 0
            
            if mw_diff < RECON_MW_TOLERANCE and pct_diff < RECON_VALUE_TOLERANCE_PCT:
                # OK — within tolerance
                status = "OK"
            elif pending_correction_exists_for_key(row.deal_id):
                # In-flight correction explains it — no action, will reconcile next cycle
                status = "PENDING"
            else:
                # Unexplained drift — needs investigation
                if auto_heal_allowed:
                    # Re-trigger batch_recompute for this key
                    trigger_batch_recompute(row.deal_id)
                    status = "AUTO_HEALED"
                else:
                    status = "ALERTED_MANUAL_INTERVENTION"
        
        # 5. Log results
        log_reconciliation_results(status, mw_diff, pct_diff, ...)
        
        sleep(RECONCILIATION_INTERVAL_MINUTES * 60)
```

### When Reconciliation Fires

**Scenario**: Postgres shows 500 MW for HB_NORTH/HE, but Gold shows 450 MW.

**Investigation**:
- Difference is 50 MW = 10%, beyond tolerance
- Check if a late nomination arrived in the last 10 minutes (might explain gap)
- If yes: log as PENDING, retry next cycle
- If no: trigger batch_recompute for affected deal_ids in that period, log as AUTO_HEALED

**Metrics emitted**:
- `reconciliation_drifts_detected` (total)
- `reconciliation_drifts_auto_healed` (healed by recompute)
- `reconciliation_drifts_alerted` (requires human review)

## Observability: Metrics-First Design

This pipeline is **heavily instrumented**. Every component emits structured metrics to help you understand **received → processed → lost → recovered** flow.

### Event Lifecycle Tracking

```
Event created (event_time=T)
    ↓
Event emitted to Kafka (producer_latency_ms)
    ↓
Event ingested to Bronze (bronze_latency_ms, events_ingested_total)
    ↓
Event appears in Silver (silver_merge_latency_ms, events_merged_total, events_deduped_total)
    ↓
Event contributes to Gold aggregation (gold_aggregation_latency_ms, events_aggregated_total)
    ↓
Gold row in Delta & Redis (end_to_end_latency_ms)
    ↓
[If correction arrives old]
    → Batch recompute triggered (recovery_triggered, recovery_latency_ms)
    ↓
    → Gold & Redis updated with corrected value
```

### Key Metrics (Prometheus format)

```
# Producer
events_emitted_total{topic="market.lmp.raw",host="producer"}
producer_latency_seconds{topic="..."}

# Bronze
events_ingested_total{topic="market.lmp.raw"}
bronze_ingest_latency_seconds{topic="..."}

# Silver
events_merged_total{topic="market.lmp.raw"}
events_deduped_total{topic="market.lmp.raw"}
events_dropped_old_corrections_total
silver_merge_latency_seconds{topic="..."}

# Gold
events_aggregated_total
events_lost_older_than_watermark_total  # Corrections that missed the watermark
recovery_triggered_total
recovery_successful_total
gold_aggregation_latency_seconds

# Reconciliation
reconciliation_drifts_detected_total
reconciliation_drifts_auto_healed_total
reconciliation_drifts_alerted_total
reconciliation_lag_seconds

# System health
kafka_consumer_lag_records
spark_structured_streaming_lag_seconds
redis_cache_hit_rate
postgres_connection_pool_active
```

### Dashboard Pages

- **Volumes**: sanity check — `received_total` should roughly equal `processed_total` (minus expected losses)
- **Latency**: is freshness within SLA? Is watermark lag increasing?
- **Positions**: live state from Redis
- **Corrections**: demo retraction
- **Reconciliation**: drift history, auto-healed vs alerted
- **System Health**: are Spark/Kafka/Redis alive? Any backlog?

## Edge Cases & Failure Modes

See [EDGE_CASES.md](./EDGE_CASES.md) for detailed documentation of:

- **Duplicate events** (network retry, producer re-send)
- **Out-of-order events** (late-arriving correction)
- **Watermark closure** (event arrives after window is closed)
- **Spark job crash** (recovery via checkpoint)
- **Kafka broker failure** (consumer group rebalance)
- **Postgres connection loss** (reconciliation retry with backoff)
- **Redis eviction** (position cache stale; refreshable from Gold)

Each failure mode is mapped to a specific test scenario and recovery pattern.

---

**Next**: Read [EDGE_CASES.md](./EDGE_CASES.md) for concrete examples of each failure mode and how the pipeline recovers. Then [AZURE_ROADMAP.md](./AZURE_ROADMAP.md) to understand the path from local to cloud.
