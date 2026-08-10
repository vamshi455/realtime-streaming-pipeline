# Roadmap: Realtime Streaming Pipeline

## Phase 1: Foundation (Current)
**Status**: 🟢 Complete documentation & planning

- [x] Project renamed to `realtime-streaming-pipeline` (production-oriented, reusable template)
- [x] Git repository initialized with semantic commit history
- [x] Core documentation:
  - README.md with quick-start, architecture diagram, Azure roadmap
  - ARCHITECTURE.md: medallion layers, watermark mechanics, recovery patterns, observability design
  - EDGE_CASES.md: 8+ failure modes with detection and recovery mechanisms
  - DESIGN_DECISIONS.md: rationale for Spark, Redpanda, medallion, watermark=4h, version-wins, dual sink, batch recompute
- [x] Visual dataflow diagram (interactive artifact): happy path, late corrections, edge cases, decision logic
- [x] CONTRIBUTING.md: contribution guidelines, code style, testing, PR process
- [x] GitHub Actions workflows: linting, testing, Docker builds

**Next step**: Docker Compose skeleton + basic services

## Phase 2: Infrastructure (Next)
**Status**: 🟡 Planned

### Milestone 2.1: Compose Skeleton
- [ ] docker-compose.yml with all services (Redpanda, Postgres, Redis, Spark, Producer, Reconcile, Dashboard)
- [ ] Health checks for each service
- [ ] Service startup ordering (topic-init → postgres/redis → spark → producer → reconcile → dashboard)
- [ ] .env file with configurable ports, watermark, latency thresholds, tolerance
- [ ] Makefile with shortcuts: `make up`, `make down`, `make health`, `make logs`
- [ ] Verify with `rpk topic list`, `psql`, `redis-cli ping`

### Milestone 2.2: Shared Models
- [ ] `shared/etrm_events/` pip-installable package
- [ ] Pydantic models: Deal, DealLeg, Nomination, MarketPrice, Position, Settlement, AuditLog
- [ ] EventEnvelope base class with lineage keys (book_id, delivery_node, settlement_period, deal_id)
- [ ] JSON schemas for each Kafka topic (v1.0)
- [ ] topics.py: topic names, partitions, key schema constants
- [ ] time_utils.py: event_time vs ingest_time helpers, watermark math
- [ ] metrics.py: CounterMetrics class, emit() helpers for event tracking
- [ ] recovery.py: dedup key patterns, recovery lookup logic

## Phase 3: Streaming Pipeline (Core Logic)
**Status**: 🟡 Planned

### Milestone 3.1: Producer & Bronze
- [ ] FastAPI async producer (`producer/app/`)
- [ ] Generators: LMP ticks (5-min ERCOT), deal events (NEW/AMENDED/CANCELLED), nominations
- [ ] Kafka producer with aiokafka, metrics emission
- [ ] Control routes: `/control/scenario/{n}` endpoints for scenario triggers
- [ ] Health check: `/health`
- [ ] Metrics endpoint: GET `/metrics` (Prometheus format)
- [ ] Bronze ingest job: raw topics → append-only Delta tables
- [ ] Verify with `rpk topic consume market.lmp.raw`

### Milestone 3.2: Silver (Dedup & Watermark)
- [ ] Silver MERGE job: version-wins dedup on Silver tables
- [ ] Watermark implementation: `withWatermark("event_time", "4 hours")`
- [ ] MERGE predicates: deal_id, deal_id+settlement_period+revision_number, delivery_node+interval_datetime
- [ ] Metrics: events_merged, events_deduped, events_dropped_old_corrections
- [ ] Unit tests: test_merge_logic.py (MERGE predicate, version-wins, out-of-order)
- [ ] Scenario S3 (duplicate dedup) becomes testable

### Milestone 3.3: Gold (Aggregation & Dual Sink)
- [ ] Gold aggregation job: windowed join (deal legs + nominations + LMP) → positions
- [ ] Dual sink: Delta MERGE + Redis HSET
- [ ] Metrics: events_aggregated, end_to_end_latency_ms, staleness_seconds
- [ ] Scenario S1 (baseline freshness) becomes observable
- [ ] Streamlit v1: positions page, staleness page reading Redis

### Milestone 3.4: Batch Recompute (Late Correction Path)
- [ ] Batch recompute job: parameterized by affected keys + time window
- [ ] Recovery watcher: detects old events in Kafka, writes to recompute.trigger
- [ ] Metrics: recovery_triggered, recovery_successful, batch_recompute_latency_ms
- [ ] Scenario S2 (3-hour-late correction) becomes testable
- [ ] Comparison: full-window replay vs targeted patch (cost measurement)

### Milestone 3.5: Effective-Dating MERGE (Out-of-Order Corrections)
- [ ] Refine Silver MERGE predicate: effective_date as primary sort, arrival_time as tiebreaker
- [ ] Scenario S6 (out-of-order corrections) becomes testable
- [ ] Unit tests: test_recovery_dedup.py (effective-dating logic)

## Phase 4: Reconciliation & Audit
**Status**: 🟡 Planned

### Milestone 4.1: Postgres Book-of-Record
- [ ] Postgres schema: position_snapshot, reconciliation_alerts, audit_log
- [ ] Seed data: books, delivery_nodes, counterparties
- [ ] Position snapshots: refreshed on schedule (e.g., hourly)

### Milestone 4.2: Reconciliation Job
- [ ] Reconcile job: compare Gold (Delta) vs Postgres (position_snapshot)
- [ ] Tolerance logic: MW tolerance + percent tolerance (configured in .env)
- [ ] Auto-heal: trigger batch_recompute for drift within tolerance threshold
- [ ] Alert: log for drift beyond tolerance
- [ ] Metrics: reconciliation_drifts_detected, reconciliation_drifts_auto_healed, reconciliation_drifts_alerted
- [ ] Scenario S4 (drift detection & healing) becomes testable

### Milestone 4.3: Audit Trail
- [ ] Audit log: entity, entity_id, prior_value, new_value, change_datetime, change_reason
- [ ] Delta history: DESCRIBE HISTORY on Silver tables (time-travel)
- [ ] Scenario S5 (audit trail) becomes testable
- [ ] Streamlit: before/after diff viewer using Delta time-travel

## Phase 5: Observability & Dashboard
**Status**: 🟡 Planned

### Milestone 5.1: Metrics Collection
- [ ] Prometheus scraping: Producer /metrics endpoint
- [ ] Spark metrics streaming: structured streaming lag, state size
- [ ] Postgres metrics: reconciliation lag, connection pool active
- [ ] Redis metrics: cache hit rate, eviction count

### Milestone 5.2: Streamlit Dashboard
- [ ] Page 1: Volumes (received → processed → lost → recovered)
- [ ] Page 2: Latency (end-to-end, watermark lag, recovery latency)
- [ ] Page 3: Positions (live from Redis + Gold fallback)
- [ ] Page 4: Corrections (retraction demo)
- [ ] Page 5: Reconciliation (drift history, auto-healed, alerted)
- [ ] Page 6: System Health (Spark lag, Kafka lag, checkpoint health)

## Phase 6: Advanced Scenarios & Resilience
**Status**: 🟡 Planned

### Milestone 6.1: Edge Case Testing
- [ ] Scenario S7 (downstream retraction): correction event propagation
- [ ] Duplicate event injection test
- [ ] Out-of-order event injection test
- [ ] Spark crash recovery test (kill -9, checkpoint recovery)
- [ ] Kafka broker failure test (assume 3x replication)
- [ ] Postgres connection loss test (retry + backoff)
- [ ] Redis eviction test (cache miss + read-through)
- [ ] Negative position validation test

### Milestone 6.2: Load & Scale Testing
- [ ] Volume test: 10K events/sec, verify metrics accuracy
- [ ] Watermark lag test: spike data volume, observe lag growth
- [ ] State size test: confirm 4h watermark ≈ 100–500 MB per node
- [ ] Latency percentiles: p50, p95, p99 end-to-end

### Milestone 6.3: Z-Order Benchmarking
- [ ] Clustering benchmark job: compare Z-Order query latency (before/after OPTIMIZE)
- [ ] Document liquid-clustering gap (Databricks-only, not available in OSS)
- [ ] Recommend when to use Z-Order vs hash partitioning

## Phase 7: Cloud & Deployment
**Status**: 🟡 Planned (Post-MVP)

### Milestone 7.1: Azure Deployment
- [ ] Replace Redpanda with Azure Event Hubs (Kafka protocol)
- [ ] Replace local Spark with Databricks or Azure Synapse
- [ ] Replace Postgres with Azure SQL or Synapse Analytics
- [ ] Replace local Delta with ADLS Gen2 mount
- [ ] Test end-to-end on Azure; document setup

### Milestone 7.2: Cloud Comparison
- [ ] Cost analysis: local Docker vs Azure (E2E)
- [ ] Performance: latency, throughput, recovery time
- [ ] Operational burden: monitoring, alerting, scaling

### Milestone 7.3: Multi-Cloud Roadmap
- [ ] AWS: Event Hubs → Kinesis, Spark → EMR, Postgres → RDS, local → S3
- [ ] GCP: Event Hubs → Pub/Sub, Spark → Dataflow, Postgres → Cloud SQL, local → GCS
- [ ] Document parity & differences

## Phase 8: Documentation & Community
**Status**: 🟡 Planned (Ongoing)

- [ ] Live architecture diagrams (Mermaid or D3)
- [ ] Troubleshooting guide: common issues, debugging tips
- [ ] Video walkthrough: architecture, scenarios, dashboard
- [ ] Domain adapters: IoT version, financial markets version
- [ ] Kafka Streams implementation (same domain logic, different runtime)
- [ ] Apache Flink implementation (true streaming, sub-10ms latency)
- [ ] Blog posts: "Why I chose Spark", "Watermark tuning", "Recovery patterns"

## Success Criteria

**MVP (Phase 3–4 complete)**:
- All 7 scenarios runnable and verified
- Dashboard shows volumes (received → processed → lost → recovered)
- Reconciliation detects & heals drift
- Batch recompute handles late corrections beyond watermark
- GitHub repo public with 500+ words of documentation
- CI/CD (linting, testing, Docker builds) passing

**Production-ready (Phase 5–7 complete)**:
- Observable: Prometheus metrics, Streamlit dashboard, alerting
- Resilient: Edge cases documented & tested, recovery mechanisms proven
- Cloud-ready: Azure deployment tested, migration guide documented
- Community: Contributions welcome, multiple domain adapters, alternative implementations

## Timeline

| Phase | Duration | Start | End |
|---|---|---|---|
| 1: Documentation | 2 weeks | Done | ✓ |
| 2: Infrastructure | 1–2 weeks | Next | TBD |
| 3: Pipeline | 3–4 weeks | After 2 | TBD |
| 4: Reconciliation | 2 weeks | After 3 | TBD |
| 5: Dashboard | 1–2 weeks | After 4 | TBD |
| 6: Advanced | 2 weeks | After 5 | TBD |
| **MVP Complete** | **~11–14 weeks total** | — | **TBD** |
| 7: Cloud | 2–3 weeks | After 6 | TBD |
| 8: Community | Ongoing | Parallel | TBD |

**Effort estimate**: 11–14 weeks to MVP (one person, part-time), with most work in Phases 3–4.

## How to Contribute

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for:
- New scenarios & edge cases
- Performance optimizations
- Alternative implementations (Kafka Streams, Flink, ClickHouse)
- Domain adapters (IoT, financial, etc.)
- Cloud deployments (Azure, AWS, GCP)
- Documentation & clarity improvements

## Links

- [Quick Start](README.md#quick-start)
- [Architecture Deep-Dive](ARCHITECTURE.md)
- [Edge Cases & Recovery](EDGE_CASES.md)
- [Design Decisions](DESIGN_DECISIONS.md)
- [Contributing Guide](.github/CONTRIBUTING.md)
