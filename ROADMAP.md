# Roadmap: Learning Event Streaming

Focused learning path: from zero to understanding how events flow through a real streaming system.

## Phase 1: Foundation (Current)
**Status**: 🟢 Complete documentation & simplified focus

- [x] Project simplified: Producer → Redpanda → Bronze (removed medallion layers Silver/Gold)
- [x] Git repository initialized with semantic commit history
- [x] Core documentation (learning-focused):
  - README.md: quick-start, simple architecture, learning goals
  - ARCHITECTURE.md: Producer, Redpanda (what is Kafka?), Bronze (why append-only?), edge cases
  - DESIGN_DECISIONS.md: why Redpanda over Kafka, why Bronze, why Delta, why partitioning matters
  - EDGE_CASES.md: duplicate events, lag, broker failures, out-of-order, storage full
  - CONTRIBUTING.md: how to extend, add new event types, run scenarios
- [x] GitHub Actions workflows: linting, testing, Docker builds

**Next step**: Docker Compose for Producer + Redpanda + Bronze consumer

## Phase 2: Infrastructure (Next)
**Status**: 🟡 Planned

### Milestone 2.1: Local Docker Compose
- [ ] `docker-compose.yml`: Redpanda broker only (Postgres, Redis, Spark, dashboard removed)
- [ ] Health checks for producer and broker
- [ ] Startup ordering: redpanda → producer
- [ ] `.env` file with configurable: Redpanda broker port, producer emit rate
- [ ] `Makefile` shortcuts: `make up`, `make down`, `make health`, `make logs`
- [ ] Verify: `rpk topic list`, `rpk topic consume`, Prometheus metrics from producer

### Milestone 2.2: Event Models
- [ ] `shared/events/` pip-installable package
- [ ] Pydantic models: LmpTick, DealEvent, NominationEvent
- [ ] JSON schema per topic
- [ ] `topics.py`: topic names, partition count, key schema
- [ ] `time_utils.py`: event_time helpers
- [ ] `metrics.py`: basic Counter emission

## Phase 3: Core Components (Implementation)
**Status**: 🟡 Planned

### Milestone 3.1: Producer
- [ ] FastAPI async server (`producer/app/main.py`)
- [ ] Event generators: LMP ticks, deal events, nominations
- [ ] aiokafka producer with serialization
- [ ] Routes: `POST /emit`, `GET /health`, `GET /metrics`
- [ ] Emit rate control (configurable events/sec)
- [ ] Metrics: `events_emitted_total`, `producer_latency_ms`

### Milestone 3.2: Bronze Consumer & Storage
- [ ] Python consumer script (`bronze/consumer.py`)
- [ ] Reads from Redpanda topics
- [ ] Appends raw messages to Delta tables (one per topic)
- [ ] Metadata: `_kafka_offset`, `_kafka_partition`, `_ingest_ts`
- [ ] Checkpoint: resume from last offset on restart
- [ ] Metrics: `events_ingested_total`, `consumer_lag`

### Milestone 3.3: Observability (Minimal)
- [ ] Prometheus scrape: producer `/metrics` endpoint
- [ ] Query tool: `scripts/query_metrics.sh` for event counts
- [ ] Simple query: "How many events received? Ingested? Lagged?"
- [ ] Log inspection: basic troubleshooting guide

## Phase 4: Learning Scenarios
**Status**: 🟡 Planned

### Scenario S1: Baseline
Emit steady stream, measure end-to-end latency (producer → Redpanda → Bronze storage).
```bash
make scenario-1
```

### Scenario S2: Duplicate Detection
Emit same event twice, observe both in Bronze. Discuss: how would you dedup? (intro to version-wins).

### Scenario S3: Consumer Lag
Emit 1000 events rapidly, measure lag. Restart consumer, observe recovery.

### Scenario S4: Broker Failure
Kill broker, show recovery via replication. Emit more events, restart broker.

### Scenario S5: Out-of-Order Events
Emit with wrong timestamps, observe in Bronze. Discuss: at what layer should you sort?

## Phase 5: Extensions (Future)
**Status**: 🟡 Planned (future learning)

- [ ] Add dedup layer (Silver, version-wins MERGE) — learn about state management
- [ ] Add aggregation layer (Gold) — learn about windowed joins
- [ ] Add reconciliation — learn about eventual consistency
- [ ] Cloud migration (Event Hubs + ADLS) — learn about managed services
- [ ] Flink/Kafka Streams implementations — compare streaming frameworks

## Success Criteria

**MVP (Phase 2–3 complete)**:
- Producer emits events, Redpanda brokers them, Bronze stores them
- Can query Bronze to see raw events
- Metrics show event flow: emitted → ingested → lag
- All 5 scenarios runnable
- Documentation explains each component

**Learning achieved**:
- Understand producer/broker/consumer pattern
- Understand why partitioning and ordering matter
- Understand Kafka protocol and Redpanda's role
- Understand append-only storage benefits
- Know how to debug lag, duplicates, failures

## Timeline

| Phase | Duration | Status |
|---|---|---|
| 1: Documentation | Done | ✓ |
| 2: Infrastructure | 1 week | Next |
| 3: Core Components | 2 weeks | After 2 |
| 4: Scenarios | 1 week | After 3 |
| **MVP Complete** | **~4 weeks** | TBD |
| 5: Extensions | Ongoing | Future |

## How to Contribute

This is a learning project. Contributions welcome:
- New event types (add to generators)
- New scenarios that expose streaming concepts
- Cloud adapters (AWS Kinesis, GCP Pub/Sub)
- Performance experiments (throughput limits, lag profiles)
- Troubleshooting guides based on your experience

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for details.

## Links

- [Quick Start](README.md#quick-start)
- [Architecture Deep-Dive](ARCHITECTURE.md)
- [Edge Cases & Failures](EDGE_CASES.md)
- [Design Decisions](DESIGN_DECISIONS.md)
- [Contributing Guide](.github/CONTRIBUTING.md)
