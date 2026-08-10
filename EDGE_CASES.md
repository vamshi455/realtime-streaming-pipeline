# Edge Cases & Failure Modes

This document catalogs every known failure mode, how the pipeline detects it, and the recovery mechanism.

| Failure Mode | Trigger | Detection | Recovery | Metric | Test Scenario |
|---|---|---|---|---|---|
| **Duplicate event** | Network retry, producer resend | Version-wins MERGE | Silver dedup keeps highest version | `events_deduped_total` | S3 |
| **Out-of-order event** | Network reordering, late server | Arrives after newer version | Silver MERGE takes higher version | `events_merged_total` | S6 |
| **Late correction (< 4h)** | Counterparty slow nomination | Watermark bounds it | Streaming path: Silver MERGE, Gold updated | `recovery_triggered` | S2 |
| **Late correction (> 4h)** | Rare, but happens | Event older than watermark | Batch recompute path triggered | `recovery_triggered`, `recovery_successful` | S2 (batch path) |
| **Spark micro-batch crash** | OOM, network error, Kafka lag spike | Job stops writing checkpoints | Resume from last checkpoint: no data loss | `spark_recovery_attempts` | Manual: kill -9 spark container |
| **Kafka broker partition failure** | Hardware failure | Consumer group lag spikes | Rebalance to replicas; assume 3x replication | `kafka_rebalance_total` | Manual: stop Redpanda container |
| **Postgres connection loss** | Network, DB crash | Reconciliation query timeout | Retry with exponential backoff; alert if > 5 min | `reconciliation_lag_seconds` | Manual: stop Postgres container |
| **Redis cache eviction** | Memory pressure, old positions | Position cache miss | Read-through: fetch from Gold Delta, refresh cache | `redis_cache_misses` | Manual: fill Redis until LRU evicts |
| **Duplicate + out-of-order** | Both network issues | v3 arrives, then v2, then v1 | MERGE keeps v3 (highest) regardless of order | `events_deduped_total`, `events_merged_total` | S3 + S6 combined |
| **Correction to already-settled deal** | Rare regulatory correction | Settlement already finalized | Batch recompute includes settlement entity; audit trail captures change | `settlement_restatement_count` | S5 (audit demo) |
| **Reconciliation drift within tolerance** | Pending late correction in Kafka | Drift detected but recent event seen | No action, reconciliation OK next cycle | `reconciliation_drifts_detected`, no alert | S4 |
| **Reconciliation drift beyond tolerance** | Data corruption, code bug, lost event | Drift unexplained by pending corrections | Auto-trigger batch_recompute if enabled; else alert | `reconciliation_drifts_alerted_total` | S4 |
| **Negative position (impossible state)** | Bug in join logic, bad data | Position aggregation produces net_mw < 0 | Data validation: reject in Gold layer, log poison-pill | `position_validation_errors` | Custom scenario |
| **Event with future timestamp** | Client clock skew | event_time > now() + buffer | Watermark ignores it; handled in catch-up mode | `events_with_skewed_time` | Custom scenario |
| **Kafka topic doesn't exist** | Deployment issue | Producer write hangs | `topic_not_found` exception caught, retry with backoff | `topic_creation_failures` | Manual: delete topic |
| **Watermark lag increasing unbounded** | Data volume spike, Spark underprovisioned | Lag continues growing each cycle | Scale Spark (local: N/A; cloud: auto-scale), reduce watermark or emit warnings | `watermark_lag_seconds` | Load test: high-volume scenario |

## Detailed Recovery Paths

### Duplicate Detection & Dedup

**Event**: LMP tick for HB_NORTH/HE arrives twice with same `(delivery_node, interval_datetime, source_version)`.

**Detection**:
```python
# Silver MERGE sees both rows with same key + version
# Predicate: WHEN MATCHED AND source_version <= existing_version THEN /* do nothing */
```

**Recovery**: The MERGE filters the duplicate silently. The aggregated position doesn't double-count.

**Verification** (Scenario S3):
```bash
# Before: events_deduped_total = 0
make scenario-3
# After: events_deduped_total = 1
# Gold row count for key stays 1
```

---

### Out-of-Order Corrections

**Event**: Correction B (effective_date=2024-08-10 16:00) arrives *before* Correction A (effective_date=2024-08-10 15:00), but A should represent the "truth" for that deal.

**Without effective-dating bug**: Final value would be from B (latest arrival), not A (correct by business time).

**Recovery**: Gold MERGE uses effective_date as primary sort key, arrival_time as tiebreaker.
```python
# Predicate
WHEN MATCHED AND (
    s.effective_date > t.effective_date 
    OR (s.effective_date == t.effective_date AND s.arrival_time > t.arrival_time)
) THEN UPDATE SET *
```

**Verification** (Scenario S6):
```bash
make scenario-6
# Sends B (effective_date=T+1h, arrival=now)
# Then sends A (effective_date=T, arrival=now+2min)
# Final Gold value should match A (effective_date=T), not B
# Assert against the "wrong" latest-arrival-wins value to prove bug would occur
```

---

### Late Correction Beyond Watermark

**Event**: Nomination amendment with event_time=T, but it arrives at wall-clock time T+5h (beyond 4h watermark).

**Streaming path failure**: Spark watermark has closed on the window [T-4h, T]; this amendment is older than the watermark and is dropped.

**Batch recovery**:

1. **Detection**: A watcher job monitors Kafka lag. It sees events in `nomination.events` that are older than current watermark but newer than the "last batch recompute checkpoint". It extracts these events.

2. **Triggering**: Watcher writes to a `recompute.trigger` topic:
   ```json
   {
     "entity_type": "nomination",
     "entity_id": "NOM-456",
     "event_time_min": "2024-08-10T01:00:00Z",
     "event_time_max": "2024-08-10T06:30:00Z",
     "reason": "late_arrival_beyond_watermark"
   }
   ```

3. **Batch job execution**:
   ```python
   # batch_recompute.py
   for trigger in consumed_from_recompute_trigger_topic:
       entity_id = trigger["entity_id"]
       
       # Read raw events from Bronze for this entity in the time window
       events = delta_table("bronze_nominations") \
           .where(f"deal_id = '{entity_id}' AND event_time BETWEEN {t_min} AND {t_max}")
       
       # Recompute Silver dedup for just this entity
       silver_rows = events \
           .groupBy("deal_id") \
           .agg(max_by_version(...)) \
           .select(silver_schema)
       
       # MERGE back into Silver (idempotent)
       silver_rows.write.format("delta").mode("merge") \
           .mergeInto("silver_nominations") \
           .on("deal_id") \
           .whenMatched... \
           .execute()
       
       # Recompute Gold for deals affected by this nomination
       deals_with_nom = silver_rows.select("deal_id").distinct()
       gold_rows = compute_gold_positions_for_deals(deals_with_nom)
       
       # MERGE back into Gold (idempotent)
       gold_rows.write.format("delta").mode("merge") \
           .mergeInto("gold_positions") \
           .on(["book_id", "delivery_node", "settlement_period"]) \
           .whenMatched... \
           .execute()
       
       # Update Redis cache for affected positions
       update_redis_from_gold(gold_rows)
   
   # Emit recovery metric
   emit_metric("recovery_triggered", 1, tags={"entity_type": "nomination", "entity_id": entity_id})
   emit_metric("recovery_successful", 1, tags={"entity_type": "nomination"})
   ```

**Verification** (Scenario S2, batch path):
```bash
make scenario-2-batch
# Inject nomination with event_time 3+ hours in past
# Assert: recovery_triggered metric incremented
# Assert: batch job recomputes and updates Gold with correct value
# Assert: Dashboard "System Health" shows recovery latency (1–5s vs 30–100ms streaming)
```

---

### Spark Job Crash & Checkpoint Recovery

**Failure**: Spark micro-batch crashes mid-write (e.g., OOM, network timeout).

**Spark Structured Streaming guarantee**: As long as the checkpoint directory is durable and survives the crash, **no data is lost**. The next restart reads the checkpoint and resumes exactly where it left off (idempotent write).

**Setup**:
```python
# In spark jobs, checkpoint config
query = df \
    .writeStream \
    .format("delta") \
    .option("checkpointLocation", "data/checkpoints/silver_merge") \
    .start()
```

**Recovery**:
1. Spark job crashes
2. Checkpoint directory persists (local: on disk; cloud: in ADLS)
3. Container restarts (Docker Compose or Kubernetes)
4. Spark reads checkpoint, sees last micro-batch ID
5. Resumes consuming Kafka from that point
6. Re-applies the same MERGE (idempotent: MERGE sees the rows already in Delta, does nothing on retry)
7. Continues normally

**Verification** (Manual):
```bash
# In one terminal, run a Spark job
docker exec spark python /spark/jobs/gold_aggregate.py &

# In another, kill it mid-run
sleep 5 && docker exec spark pkill -9 python

# Check checkpoint
docker exec spark ls -lh data/checkpoints/gold_aggregate/

# Restart container; Spark resumes
docker restart spark_container

# Verify: no data was lost (row count in Gold continues from checkpoint, not duplicated)
```

---

### Postgres Connection Loss & Reconciliation Retry

**Failure**: Reconciliation job tries to query Postgres, but connection is down.

**Recovery**:
```python
# reconcile_job.py
def reconciliation_job():
    while True:
        try:
            postgres_positions = pd.read_sql(query, postgres_conn, timeout=30)
        except (psycopg2.Error, TimeoutError) as e:
            logger.error(f"Reconciliation query failed: {e}")
            emit_metric("reconciliation_lag_seconds", time.time() - last_success)
            
            if time.time() - last_success > 300:  # 5 min threshold
                emit_alert("reconciliation_stalled_5min")
            
            # Exponential backoff
            wait_time = min(300, backoff_seconds * 2)
            sleep(wait_time)
            continue
        
        # Query succeeded, reset backoff
        backoff_seconds = 1
        last_success = time.time()
        
        # ... rest of reconciliation logic
```

**Verification**:
```bash
# Stop Postgres
docker stop postgres

# Observe reconciliation job logging retries with backoff
docker logs reconcile

# Restart Postgres
docker start postgres

# Observe reconciliation resumes and catches up
```

---

### Redis Cache Eviction & Read-Through

**Failure**: Redis fills up (local memory pressure or misconfigured eviction policy). An old position is evicted (e.g., HB_NORTH/HE from 3 hours ago).

**Read path during cache miss**:
```python
# Dashboard wants to show all positions
positions = []
for key in get_all_position_keys():
    try:
        value = redis.hgetall(key)  # Cache hit
        positions.append(value)
    except KeyError:
        # Cache miss; refresh from Gold Delta
        value = gold_positions \
            .filter(parse_key(key)) \
            .select("net_mw", "mtm_value", "as_of_datetime", "source_version") \
            .limit(1) \
            .collect()[0]
        
        # Update cache
        redis.hset(key, mapping=value)
        
        emit_metric("redis_cache_misses", 1)
        positions.append(value)

# All positions always consistent; some are slightly fresher than others
```

**Verification**:
```bash
# Fill Redis until LRU evicts old positions
docker exec producer python -c "
    import redis
    r = redis.Redis(host='redis', port=6379)
    # Write megabytes of junk data
    for i in range(100000):
        r.hset(f'junk:{i}', mapping={'x': str(i) * 1000})
"

# Observe dashboard still shows all positions (via cache miss + read-through)
# Verify: redis_cache_misses metric incremented
```

---

## Adding New Edge Cases

When you discover a new failure mode:

1. **Document** it in this table above
2. **Write a test scenario** in `scripts/run_scenario_N.sh` or a new scenario
3. **Emit a metric** to track occurrences: `emit_metric("my_edge_case_count", 1)`
4. **Verify** the recovery in the dashboard or logs
5. **Update** the appropriate layer (Bronze, Silver, Gold, Reconciliation) to handle it gracefully

---

See [ARCHITECTURE.md](./ARCHITECTURE.md) for architectural context, and [DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md) for why certain recovery patterns were chosen over alternatives.
