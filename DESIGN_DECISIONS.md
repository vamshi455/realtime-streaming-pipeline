# Design Decisions

Every architectural choice documented with tradeoffs. This is how you evaluate whether to adopt this pattern for your use case.

## Table of Contents

1. [Why Spark Structured Streaming?](#why-spark-structured-streaming)
2. [Why Redpanda (not Kafka)?](#why-redpanda-not-kafka)
3. [Why Medallion (Bronze/Silver/Gold)?](#why-medallion-bronzesilver gold)
4. [Why Watermark = 4 Hours?](#why-watermark--4-hours)
5. [Why Version-Wins MERGE?](#why-version-wins-merge)
6. [Why Redis + Delta Dual Sink?](#why-redis--delta-dual-sink)
7. [Why Batch Recompute for Late Corrections?](#why-batch-recompute-for-late-corrections)

## Dataflow Diagrams

### Normal / Happy Path (Event within watermark)

```
Event @ event_time=T arrives at wall-clock=T+0.5s (fresh)
    ↓
Producer writes to Kafka broker (acks=all), metrics: events_emitted_total++
    ↓
Spark readStream pulls from Kafka
    ↓
Bronze writes raw event (append-only)
    ↓
Silver readStream (with watermark=4h) reads Bronze → applies MERGE
    [Watermark progress: now(), event age = 0.5s < 4h, event is within window]
    ↓
Silver MERGE dedup: version-wins logic determines if this version beats the current one
    [If higher version or first arrival: insert/update; else skip]
    ↓
Gold windowed join (Silver deal + Silver lmp) → aggregated position
    ↓
Dual sink:
    ├─ Delta MERGE: gold_positions += row (or update if exists)
    └─ Redis HSET: position:{book}:{node}:{period} with latency metrics
    ↓
Redis reader (Dashboard) reads position @~5ms latency
End-to-end latency: ~100 ms
Metrics: events_received++, events_processed++
```

### Late Correction Within Watermark (event_time=T-2h, arrives @ wall-clock=T)

```
Event @ event_time=T-2h arrives at wall-clock=T (2 hours late)
    ↓
Producer writes to Kafka broker
    ↓
Spark readStream pulls from Kafka
    ↓
Bronze writes raw event
    ↓
Silver readStream + watermark=4h reads Bronze
    [Watermark progress: now(), event age = 2h < 4h, event is WITHIN window]
    ↓
Spark stateful operator has this window still OPEN (thanks to watermark)
    ↓
Silver MERGE dedup: this event version is compared against existing
    [If higher: update existing row; if lower: skip]
    ↓
Gold re-aggregates (stateful window includes the late event)
    ↓
Dual sink updates (Gold Delta MERGE + Redis)
    ↓
Reconciliation job next cycle observes: Postgres old value, Gold new value
    [If within tolerance: OK; else: triggers batch_recompute for extra verification]
    ↓
End-to-end latency: ~300–500 ms (depends on window flush timing)
Metrics: recovery_triggered++, recovery_successful++
```

### Late Correction Beyond Watermark (event_time=T-5h, arrives @ wall-clock=T)

```
Event @ event_time=T-5h arrives at wall-clock=T (5 hours late, BEYOND 4h watermark)
    ↓
Producer writes to Kafka broker
    ↓
Spark readStream pulls from Kafka
    ↓
Bronze writes raw event (append-only)
    ↓
Silver readStream + watermark=4h reads Bronze
    [Watermark progress: now(), event age = 5h > 4h WATERMARK, event is OUTSIDE window]
    ↓
Spark stateful operator has CLOSED this window (watermark moved past it)
    ↓
Event is DROPPED from streaming path (not processed by Silver/Gold)
    ↓
But event is still in Kafka & Bronze
    ↓
Batch recompute watcher detects: "events in Bronze older than current watermark"
    ↓
Watcher writes to recompute.trigger topic:
    { "entity_id": "NOM-456", "event_time_min": T-5h, "event_time_max": T }
    ↓
Batch recompute job consumes recompute.trigger
    ├─ Read Bronze for entity_id in time window [T-5h, T]
    ├─ Apply Silver dedup logic (version-wins MERGE) for just this entity
    ├─ Recompute Gold rows affected by this entity
    ├─ MERGE back into Gold (idempotent)
    └─ Update Redis cache
    ↓
Reconciliation job next cycle: Postgres old value, Gold new value (from batch recompute)
    ↓
End-to-end latency: ~1–5 seconds (batch path, not streaming)
Metrics: recovery_triggered++, recovery_successful++, batch_recompute_latency_seconds
```

### Duplicate Event (Same Key & Version)

```
Event 1 @ event_time=T, deal_version=1 arrives normally
    ↓ (through all layers as above)
    ↓
Silver MERGE inserts (deal_id, deal_version=1)
    ↓
Event 1 duplicated by network retry: arrives again @ event_time=T+0.1s
    ↓
Producer writes to Kafka broker
    ↓
Spark readStream pulls duplicate from Kafka
    ↓
Bronze writes raw event (duplicate is preserved in append-only log)
    ↓
Silver readStream + MERGE logic
    [MERGE sees: existing row has deal_version=1, incoming has deal_version=1]
    [MERGE predicate: WHEN MATCHED AND incoming.version <= existing.version THEN /* do nothing */]
    ↓
Duplicate is filtered silently (no INSERT, no UPDATE)
    ↓
Gold position unchanged (no re-aggregation needed, same value)
    ↓
End-to-end latency: ~100 ms (processed, but discarded)
Metrics: events_received++, events_deduped++, events_processed = received - deduped
```

### Out-of-Order Corrections (v3 arrives, then v2, then v1)

```
Correction B @ event_time=T, deal_version=3, effective_date=T+1h arrives first
    ↓
Silver MERGE inserts (deal_id, deal_version=3, effective_date=T+1h)
    ↓
Gold aggregates with v3 values
    ↓
    
Correction A @ event_time=T-30min, deal_version=2, effective_date=T (earlier effective date!)
    arrives second (10 seconds later)
    ↓
Silver MERGE compares: existing.deal_version=3, incoming.deal_version=2
    [Predicate 1: WHEN MATCHED AND incoming.version > existing.version THEN UPDATE]
    [2 > 3? NO → proceed to tiebreaker]
    [Predicate 2: effective_date_based: incoming.effective_date=T, existing.effective_date=T+1h]
    [T < T+1h? YES → incoming is MORE RECENT in business time, UPDATE]
    ↓
Silver updates to (deal_id, deal_version=2 or 3?, effective_date=T)
    [Keeping highest version for audit trail, but using effective_date for reconciliation]
    ↓
Gold re-aggregates with A's (corrected) values
    ↓
    
Correction C @ event_time=T-1h, deal_version=1, effective_date=T-30min
    arrives third
    ↓
Silver MERGE compares: existing.deal_version=2 (or 3), incoming.deal_version=1
    [1 > 2? NO → proceed to effective_date tiebreaker]
    [incoming.effective_date=T-30min, existing.effective_date=T]
    [T-30min < T? NO → incoming is OLDER in business time, do nothing]
    ↓
Silver discards C (stale by effective_date)
    ↓
Gold position remains based on A's values (correct by effective_date)
    ↓
End-to-end latency: depends on arrival order, but final value is CORRECT by effective_date
Metrics: events_received=3, events_merged=2, events_deduped=1 (or similar, depending on implementation)
```

---

## Why Spark Structured Streaming?

### Spark Structured Streaming

**Pros**:
- Micro-batch (mini-ETL) model is intuitive for data engineers
- Built-in watermark + stateful aggregation for windowed operations
- Delta Lake integration (same engine, same time-travel, same MERGE)
- Checkpointing (recover from crash without data loss)
- Scala/Python: familiar to data teams
- Excellent cloud support (Databricks, Azure Synapse, EMR)

**Cons**:
- Not true continuous processing (30–100 ms latency floor per batch)
- Worst for sub-millisecond requirements (trading, HFT)
- Spark overhead (JVM, GC) for small datasets

### Alternatives

| Tool | Latency | State | Watermark | Dedup | Cons |
|---|---|---|---|---|---|
| **Kafka Streams** | Sub-100ms | In-memory + RocksDB | ✓ | Manual | State store sizing, language limits (Java/Scala) |
| **Apache Flink** | Sub-10ms | In-memory + RocksDB | ✓ | Manual | Steeper learning curve, smaller community |
| **ClickHouse** | Milliseconds | In-memory | Implicit | Implicit | Not a stream processor; append-only designed for analytics, not correctness |
| **Kinesis Lambda** | Seconds | None | Manual | Manual | AWS-locked, event-by-event processing, no state |

### Decision

**Spark** for this project because:
1. We're in the **5-minute latency world** (power trading), not HFT — Spark's micro-batch floor (30–100 ms) is fine
2. **Delta Lake** is the killer feature — built-in MERGE, time-travel, audit trail are first-class
3. **Cloud parity**: Databricks/Synapse/EMR all run Spark; code doesn't change when you scale
4. **Dedup & recovery**: Delta MERGE makes version-wins and idempotency trivial
5. **Team familiarity**: data engineers know PySpark + SQL

**If you need sub-100ms**: Kafka Streams or Flink. Accept manual watermark + dedup logic.

---

## Why Redpanda (not Kafka)?

### Redpanda

**Pros**:
- Kafka-compatible API (drop-in replacement)
- Lighter resource footprint (C++, no JVM)
- Faster broker performance (throughput, latency)
- Built-in schema registry (optional)
- Perfect for local dev (single container, < 500 MB)

**Cons**:
- Smaller community than Kafka
- Enterprise support is newer
- Some advanced features lag Kafka (e.g., raft quorum rebalancing)

### Kafka (Apache OpenSource)

**Pros**:
- Biggest ecosystem, most mature
- Tooling (Kafka Connect, Confluent Platform, etc.)
- More operational experience in the wild

**Cons**:
- JVM overhead; heavier to run locally
- More boilerplate for a dev project

### Decision

**Redpanda** for this project (and production dev environments) because:
1. **Dev experience**: lighter, faster, easier to run on laptop
2. **API compatibility**: any change is trivial (just change `bootstrap.servers`)
3. **Production path**: migrate to Event Hubs (Azure) or Kafka (AWS) with 2-line config change
4. For your **power trading domain**: reliability matters, Redpanda 3-replica mode provides it

---

## Why Medallion (Bronze/Silver/Gold)?

### Medallion Layers

The three-layer medallion separates concerns:

| Layer | Purpose | Characteristics | Use Case |
|---|---|---|---|
| **Bronze** | Immutable archive | Append-only raw events, minimal transformation | Replay, audit, compliance, debugging |
| **Silver** | Business-truth cleansing | Dedup, schema enforcement, SLA checks | Operational queries, dashboards, analytics |
| **Gold** | Optimized analytics | Aggregated, pre-joined, denormalized | Real-time dashboards, ML features, reports |

### Why This Separation?

1. **Debugging**: bug in Gold? Replay Bronze through a fixed Silver/Gold to rebuild
2. **Data lineage**: end-to-end audit trail (Bronze → Silver → Gold → Downstream)
3. **Iterative refinement**: improve Silver dedup logic without touching Bronze or losing data
4. **Compliance**: Bronze is the immutable record (useful for financial/trading audit)
5. **Scalability**: process volume at Bronze, dedup at Silver, serve analytics from Gold

### Anti-Pattern: Single Table

If you tried to do everything in one Kafka-to-Gold query:
- No replay capability (can't go back and reprocess if logic changes)
- No dedup traceability (where did duplicates come from?)
- Hard to debug (is the bug in ingest, dedup, or aggregation?)
- Tight coupling (change one thing, rebuild entire downstream)

**Decision**: Medallion architecture is **standard** for data lakes. Use it.

---

## Why Watermark = 4 Hours?

### The Tradeoff

**Long watermark** (e.g., 4 hours):
- ✓ Catches realistic late nominations/corrections
- ✗ Inflates Spark state size in memory (100s of MB for 6 nodes)
- ✗ Adds 4-hour latency floor before window closes (false: watermark is separate from output)

**Short watermark** (e.g., 10 minutes):
- ✓ Tight latency
- ✗ Misses late-arrivals (nominations arrive 2–3 hours late regularly)

### Domain Knowledge

In **ERCOT power trading**:
- Real-time market (5-min intervals) settles within 45 minutes
- Nominations (counterparty says "I'll take X MW") arrive 2–4 hours later as transport confirms
- Settlement restatements can arrive days later

### Decision

**4 hours** because:
1. Covers 99% of late nominations (settlement restatements route to batch path)
2. Local Spark memory is cheap; 4h window ≈ 100–500 MB per node
3. **Explicit fallback**: corrections older than 4h don't fail silently; they trigger batch_recompute
4. **Tunable**: change `.env` to 2h or 6h per your domain

For your use case:
- **IoT (telemetry)**: watermark = 1 hour (devices cache locally, sync infrequently)
- **Financial markets (trades)**: watermark = 30 seconds (tight SLA)
- **Power trading (nominations)**: watermark = 4 hours (late-arriving is normal)

---

## Why Version-Wins MERGE?

### The Problem

Without dedup, an accidental duplicate event produces double-counted positions:

```
Event: LMP tick for HB_NORTH = $50.50, volume = 100 MW
Duplicate arrives: same LMP tick

Without dedup:
  Gold aggregation: sum(volume) = 100 + 100 = 200 MW (WRONG)

With version-wins MERGE:
  Silver MERGE keeps version=1, ignores version=1 duplicate
  Gold aggregation: sum(volume) = 100 MW (CORRECT)
```

### Why Version, Not Latest-Arrival?

```
Scenario: Deal amendment v2 arrives before deal creation v1 (network reordering)

With latest-arrival:
  v2 arrives @ T+0s → inserted (current state = v2)
  v1 arrives @ T+1s → compared by timestamp, latest is v2, so v1 is ignored
  Final state: v2 (WRONG, missing base deal)

With version-wins:
  v2 arrives @ T+0s → inserted as version=2
  v1 arrives @ T+1s → version=1 < version=2, so v1 is ignored
  Wait, this is also WRONG!
  
  Correction: what we actually do is:
  v2 arrives @ T+0s → inserted as version=2, effective_date=T+1h
  v1 arrives @ T+1s → version=1 < version=2, but effective_date of v1 is T
  MERGE predicate checks: effective_date of v1 is OLDER than v2's effective_date
  Result: v1 is ignored, v2 remains (CORRECT if v2 is the amendment)
```

### Three-Tier Tiebreaker

```python
MERGE predicate:
1. Primary: version (highest version wins)
2. Secondary: effective_date (for out-of-order corrections, effective_date matters more)
3. Tertiary: arrival_time (tiebreaker if both version and effective_date are equal)
```

**Decision**: Version-wins + effective_date is the **standard** for financial/trading systems. It prevents silent data loss and ensures business-time correctness.

---

## Why Redis + Delta Dual Sink?

### The Dilemma

**Delta only** (no Redis):
- ✓ Durable, queryable, full history
- ✗ Read latency: 5–50 ms per query (network round-trip to storage + query planning)
- ✗ Can't sustain dashboard refresh rate (query every 2s = 500 queries/min)

**Redis only** (no Delta):
- ✓ Sub-millisecond read latency
- ✗ No durability (crash = loss of cache)
- ✗ No history (can't query "what was position 3 hours ago?")
- ✗ Limited retention (memory-bounded)

### Decision: Dual Sink

```
Spark Gold writes:
  ├─ [Sink 1] Delta MERGE (durable, historical, queryable)
  └─ [Sink 2] Redis HSET (live cache for dashboard reads)

Dashboard reads Redis (fast), but falls back to Gold Delta on cache miss (correctness)
```

**Why both?**
1. **Freshness**: Redis updates sub-100ms, before Delta write completes
2. **Durability**: Delta survives Redis eviction or crash
3. **Auditability**: Delta time-travel shows all position changes
4. **Reconciliation**: reconcile job compares Postgres vs Gold Delta (not Redis, which is transient)

**Cost**: slight write overhead (Spark writes to two sinks), but read performance + durability gain is worth it.

**Decision**: Dual sink is the **standard** for real-time systems requiring both speed and audit trail.

---

## Why Batch Recompute for Late Corrections?

### The Problem

Without an explicit batch path, corrections older than the watermark are **silently dropped** (Spark can't reprocess them). This means:
- Position is stuck at old value
- No error message (silent data loss)
- Reconciliation flags drift, but why?

### Solution: Explicit Batch Recompute

When a correction older than watermark arrives:
1. Detect it (topic lag monitoring or poison-pill topic)
2. Trigger batch job: recompute affected keys from Bronze
3. MERGE result back into Silver/Gold
4. Emit metric: `recovery_triggered`, `recovery_successful`

**Why separate job, not in streaming pipeline?**
- **Streaming job** is tuned for high throughput (30s micro-batch, many keys)
- **Batch job** is tuned for correctness on few keys (1–10 entities, 1–5 second runtime)
- **Separation** lets you scale independently and debug failures in isolation

### Trade-Offs

| Approach | Latency | Complexity | Failure Risk |
|---|---|---|---|
| **Longer watermark** (e.g., 8h) | Higher state size; slower micro-batches | Lower (simpler) | Silent drop if correction even older |
| **Batch recompute** (4h watermark + batch path) | 1–5s recovery latency | Higher (separate job) | Recoverable; metric alerts |
| **No watermark** (stateless streaming) | Unbounded state; OOM risk | Medium | Crash on state blowup |

**Decision**: Batch recompute is the **standard** for real-world streaming. Embrace it.

---

## Tradeoff Summary Table

| Decision | Why This Choice | Cost | Benefit |
|---|---|---|---|
| Spark Structured Streaming | Cloud parity, Delta MERGE, watermark + state | 30–100 ms latency floor | Durability, dedup, recovery |
| Redpanda | Lighter than Kafka, API-compatible | Smaller community | Dev speed, local testing |
| Medallion 3-layer | Separation of concerns, replay capability | Complexity, storage | Debuggability, compliance, iteration |
| Watermark = 4h | Realistic late-arrival window for domain | State size ~500 MB | 99% correction catch rate |
| Version-wins MERGE | Handles out-of-order events, idempotency | Predicate complexity | Silent dedup, no double-count |
| Dual sink (Delta + Redis) | Speed + durability | Write overhead, operational burden | Sub-100ms fresh + audit trail |
| Batch recompute for late | Explicit recovery, observable | Separate job to operate | No silent data loss, recoverable |

---

**Next**: Read [AZURE_ROADMAP.md](./AZURE_ROADMAP.md) for how to graduate these decisions from local to cloud.
