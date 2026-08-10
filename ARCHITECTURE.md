# Streaming Architecture: Producer → Broker → Storage

This document explains how events flow from producers through Redpanda (Kafka-compatible broker) into Bronze storage. Designed for learning the fundamentals of event-driven data systems.

## Table of Contents

1. [System Overview](#system-overview)
2. [Producer: Event Emission](#producer-event-emission)
3. [Redpanda: The Event Broker](#redpanda-the-event-broker)
4. [Bronze: Raw Data Storage](#bronze-raw-data-storage)
5. [Data Flow & Guarantees](#data-flow--guarantees)
6. [Edge Cases & Recovery](#edge-cases--recovery)

## System Overview

A minimal, learning-focused event streaming pipeline:

```
Producer (FastAPI)
    ↓
    Events emitted to Redpanda topics
    ↓
Redpanda (Event Broker)
    ↓
    Topics partition events by key
    ↓
Bronze (Raw Storage)
    ↓
    Append-only Delta tables
```

**Goal**: Learn how events flow through a system. No transformation, dedup, or aggregation—just reliable event capture and storage.

---

## Producer: Event Emission

**Role**: Generate and emit events to Redpanda.

**Characteristics**:
- FastAPI async application
- Emits to Redpanda topics keyed by entity (e.g., deal_id, delivery_node)
- Topics: `market.lmp.raw`, `deal.events`, `nomination.events`
- Emits per scenario or on demand via control routes

**Example**:
```python
# In producer/app/main.py
async def emit_lmp_tick(delivery_node, lmp_value, event_time):
    message = {
        "delivery_node": delivery_node,
        "lmp": lmp_value,
        "event_time": event_time,
        "ingest_time": datetime.now().isoformat()
    }
    await kafka_producer.send(
        topic="market.lmp.raw",
        key=delivery_node.encode(),
        value=json.dumps(message).encode()
    )
```

**Health check**: `curl http://localhost:8000/health`

---

## Redpanda: The Event Broker

**What is Redpanda?**
Redpanda is a Kafka-compatible event broker—a distributed message queue that:
- Accepts events from producers
- Stores them in partitioned topics
- Delivers them to consumers in order (per partition)
- Guarantees durability (replication)

Think of it as a reliable, high-performance pipe between systems.

**Why Redpanda instead of Kafka?**
- Same protocol (Kafka clients work unchanged)
- Simpler to run locally (single binary vs JVM ecosystem)
- Faster (written in C++, no GC pauses)
- Better for learning (easier mental model)

**Topics in this system**:
- `market.lmp.raw`: LMP price ticks (5-min intervals)
- `deal.events`: Deal captures (NEW/AMENDED/CANCELLED)
- `nomination.events`: Nomination updates (revisions, amendments)

Each topic has **partitions** (default: 6). Events are partitioned by key (e.g., deal_id), so all events for a given deal go to the same partition. Consumers see them in order within that partition.

**Inspect Redpanda**:
```bash
# List topics
docker exec redpanda rpk topic list

# Consume a topic (last 10 messages)
docker exec redpanda rpk topic consume market.lmp.raw --num 10

# Check topic lag
docker exec redpanda rpk group describe bronze-ingest
```

---

## Bronze: Raw Data Storage

**Purpose**: Immutable, append-only record of every event.

**Characteristics**:
- Delta tables (one per Redpanda topic)
- Schema: minimal transformation
  - `_raw_payload`: exact bytes from Kafka
  - `_kafka_offset`: message offset in partition
  - `_kafka_partition`: which partition
  - `_ingest_ts`: when Bronze received it
- No dedup, no filtering, no schema enforcement (raw = raw)
- Append-only: events never overwritten or deleted
- Full replay capability: can reprocess from any offset

**Why Bronze?**
- If something breaks downstream, replay from Bronze
- Audit trail: every event that ever arrived, exactly as received
- Debugging: inspect raw payloads, check schema evolution
- No data loss: even if consumers fail, Bronze preserves everything

**Schema**:
```sql
CREATE TABLE bronze_market_lmp (
    _raw_payload STRING,          -- exact Kafka message value
    _kafka_offset LONG,           -- position in partition
    _kafka_partition INT,         -- which partition
    _ingest_ts TIMESTAMP,         -- when we ingested it
    _file_path STRING,            -- Delta table path
    _added_ts TIMESTAMP           -- metadata
)
```

**Example query** (after events arrive):
```sql
-- Count events received in last hour
SELECT COUNT(*) FROM bronze_market_lmp
WHERE _ingest_ts >= now() - interval 1 hour;

-- Inspect a raw event
SELECT _raw_payload FROM bronze_market_lmp LIMIT 1;

-- Lag: oldest event still in storage
SELECT MIN(_ingest_ts) as oldest_event FROM bronze_market_lmp;
```

## Data Flow & Guarantees

### The Journey of an Event

1. **Producer emits**: Event created with business timestamp (`event_time`) and emitted to Redpanda topic
2. **Broker receives**: Redpanda assigns message an offset, appends to partition, replicates to other brokers
3. **Consumer reads**: Bronze consumer connects to Redpanda, reads message at offset
4. **Storage**: Raw message stored in Delta table with Kafka metadata (`_kafka_offset`, `_kafka_partition`, `_ingest_ts`)
5. **Done**: Event immutably stored, available for later replay

### Guarantees

**Durability**: Events written to Redpanda are replicated (default: 3 copies). If one broker fails, replicas keep data.

**Ordering**: Events emitted to the same partition (via same key) arrive in order. Different partitions have no ordering guarantee.

**Idempotency**: Bronze appends every event. If Bronze consumer crashes and restarts, it replays from the last offset—events aren't lost or duplicated.

### Latency Profile

- **Producer → Redpanda**: <1ms (network)
- **Redpanda → Bronze consumer**: <10ms (internal)
- **Bronze write to Delta**: ~100ms (disk I/O)
- **End-to-end (event creation to durable storage)**: ~100–200ms

### Example Data Flow

```bash
# 1. Producer emits LMP tick
curl -X POST http://localhost:8000/emit \
  -H "Content-Type: application/json" \
  -d '{"delivery_node": "HB_NORTH", "lmp": 45.50, "event_time": "2024-08-10T15:30:00Z"}'

# 2. Event written to Redpanda topic
# (Broker: appends to market.lmp.raw topic, partition 0, offset 12345)

# 3. Bronze consumer reads it
# (Consumer: reads offset 12345, extracts raw JSON payload)

# 4. Event stored in Bronze
# (Delta: appended to bronze_market_lmp table with _ingest_ts, _kafka_offset, etc.)

# 5. Query Bronze to verify
SELECT _raw_payload, _ingest_ts FROM bronze_market_lmp
WHERE _kafka_partition = 0 AND _kafka_offset = 12345;
```

---

## Edge Cases & Recovery

### 1. Duplicate Events (Network Retry)

**Scenario**: Producer doesn't get ack from Redpanda, retries sending same message. Broker receives two copies.

**What happens**: Both messages land in Redpanda, Bronze appends both. Bronze consumer sees two rows with identical `_raw_payload` but different `_kafka_offset`.

**Detection**: Query Bronze, group by `_raw_payload`, count > 1 means duplicates.

**Prevention**: Producer-side dedup key (idempotent sends) or application-level dedup on the raw payload hash.

### 2. Consumer Lag (Slow Processing)

**Scenario**: Events arrive in Redpanda, but Bronze consumer falls behind (network hiccup, slow disk).

**What happens**: `kafka_consumer_lag` metric grows. Events sit in Redpanda broker buffer. If lag exceeds retention period, oldest events are deleted.

**Detection**: Monitor `rpk group describe bronze-ingest` for lag. Alert if lag > retention.

**Recovery**: Restart Bronze consumer, or increase Redpanda retention time.

### 3. Broker Failure

**Scenario**: One Redpanda broker crashes (simulated: `docker kill redpanda`).

**What happens**: Cluster rebalances (default: 3x replication). Other brokers take over. Consumer sees brief pause, then resumes.

**Detection**: Monitor broker health via `rpk status`.

**Recovery**: Redpanda handles automatically with replication.

### 4. Bronze Storage Full

**Scenario**: Delta table grows unbounded. Local disk fills.

**What happens**: Bronze write fails. Consumer thread crashes. No more events appended.

**Detection**: Monitor disk usage on container.

**Recovery**: Implement retention policy (delete old partitions) or use cloud storage (ADLS Gen2).

### 5. Out-of-Order Events

**Scenario**: Producer emits event A at 15:30, then event B at 15:29 (clock skew).

**What happens**: Both stored in Bronze in arrival order (B then A in storage), not event_time order.

**Detection**: Query Bronze, sort by `_raw_payload.event_time`, compare to `_kafka_offset` order. They won't match.

**Recovery**: Downstream systems handle ordering (not Bronze's job). Bronze just captures what arrived.

---

**Next**: Run the [Quick Start](README.md#quick-start) to see this in action. Then explore [Producer](#producer-event-emission) and [Redpanda](#redpanda-the-event-broker) code examples.
