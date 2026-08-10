# Contributing to Realtime Streaming Pipeline

This project is designed as a learning resource and reusable template for event-driven streaming architectures. Contributions are welcome!

## Contribution Areas

### 1. New Scenarios
Found a new edge case or failure mode? 
- Document it in [EDGE_CASES.md](../EDGE_CASES.md)
- Add a test scenario in `scripts/run_scenario_*.sh`
- Emit a metric to track it
- Verify recovery works

### 2. Performance & Scalability
- Optimize Spark jobs (reduce shuffle, better partitioning)
- Benchmark Z-Order vs future liquid clustering
- Profile latency under load
- Contribute load-testing scenarios

### 3. Alternative Implementations
- Kafka Streams version (same domain logic, different runtime)
- Apache Flink version (true streaming, sub-10ms latency)
- ClickHouse version (append-only analytics, different architecture)
- Contribute alongside the main Spark implementation for comparison

### 4. Domain Adapters
- Rename `etrm_events` → `iot_events`, `financial_events`, etc.
- Adapt schemas and business logic for your domain
- Document the adaptation process
- Share as a separate reference or branch

### 5. Cloud Deployments
- Azure: Event Hubs + Synapse + ADLS Gen2
- AWS: Kinesis + EMR + S3
- GCP: Pub/Sub + Dataflow + GCS
- Document the setup and cost tradeoffs

### 6. Documentation & Clarity
- Fix unclear sections in ARCHITECTURE.md, EDGE_CASES.md, or DESIGN_DECISIONS.md
- Add more visual diagrams (dataflow, recovery flows)
- Expand TROUBLESHOOTING.md with real scenarios
- Translate key docs to other languages

## Code Style

- **Python**: Follow PEP 8; use `black` for formatting, `pylint` for linting
- **SQL**: Clear indentation, CTE-first style for complex queries
- **Shell scripts**: Bash 4+, `shellcheck` clean
- **Markdown**: Semantic headings, code blocks with language tags, links to related docs

## Testing

```bash
# Run unit tests
make test

# Check code coverage
make coverage

# Lint & format
make format
make lint
```

## Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `infra`

**Example**:
```
feat: add effective-date MERGE predicate for out-of-order corrections

Implement business-time-based dedup in Silver layer.
Corrections now resolve by effective_date, not arrival order.

Fixes: #42
Related: DESIGN_DECISIONS.md#version-wins-merge
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

## Opening an Issue

Include:
1. **What you observed** (the behavior)
2. **What you expected** (the desired behavior)
3. **Steps to reproduce** (if applicable)
4. **Logs or metrics** (if applicable)
5. **Which scenario** this affects (S1–S7 or custom)

Example:
```
Title: Reconciliation drift detection not triggering

I injected a 100 MW drift into Postgres (beyond tolerance).
Expected: `reconciliation_drifts_detected` metric should increment.
Observed: No metric emitted; no alert.

Steps:
1. make scenario-4
2. docker exec postgres psql -c "UPDATE position_snapshot SET net_mw = 100 WHERE ..."
3. Observe reconciliation job output
4. Check metrics

Environment: local Docker, Spark 3.4.0, Delta 3.0.0
```

## Opening a Pull Request

Link your PR to the issue it addresses. Provide:
1. **What changed** (summary of commits)
2. **Why** (reasoning, tradeoffs)
3. **How to test** (commands to verify)
4. **Metrics before/after** (if performance-related)

Example PR description:
```
## Summary

Implements batch recompute for corrections older than watermark (addresses #42).
- New file: `spark/jobs/batch_recompute.py`
- New file: `shared/etrm_events/recovery.py`
- Updated: `ARCHITECTURE.md`, `EDGE_CASES.md`

## Testing

```bash
make scenario-2-batch
# Should see recovery_triggered, recovery_successful metrics
# Assert: batch job recomputes and updates Gold with correct value
```

## Tradeoffs

- Adds complexity: second job to operate and monitor
- Benefit: no silent data loss; explicit recovery observable via metrics
- Latency: 1–5s batch path vs 100ms streaming path (acceptable for 3h late corrections)

Closes #42
```

## Architecture Decisions

Before proposing major architectural changes, check [DESIGN_DECISIONS.md](../DESIGN_DECISIONS.md). It documents the reasoning behind:
- Why Spark Structured Streaming (not Kafka Streams/Flink)
- Why Redpanda (not Kafka)
- Why medallion architecture (Bronze/Silver/Gold)
- Why watermark = 4 hours
- Why version-wins MERGE
- Why dual sink (Delta + Redis)
- Why batch recompute for late corrections

If you disagree with a decision, open an issue first to discuss before sending a PR.

## License

By contributing, you agree your contributions are licensed under MIT (same as the project).

---

**Questions?** Open an issue, check TROUBLESHOOTING.md, or read ARCHITECTURE.md.

**First time?** Start with [Quick Start](../README.md#quick-start), run a scenario, then pick a contribution area that interests you.
