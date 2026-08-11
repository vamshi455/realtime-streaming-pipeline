# Integration Guide - React Dashboard + Producer API + Kafka → SMB

Complete end-to-end integration for the Synthetic Data Studio with real data flow through the pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Synthetic Data Studio                           │
│                     (React + TypeScript)                        │
│  http://localhost:5173 - Dashboard UI                          │
│  - Loads dataset from GET /dataset                             │
│  - Configures PII masking strategies                           │
│  - Triggers generation with POST /emit/batch                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Producer API (FastAPI)                         │
│                  http://localhost:8000                          │
│  - GET /dataset: Returns dataset config (Tables, Fields, PII)  │
│  - POST /emit/batch: Generates events, sends to Kafka          │
│  - GET /health: Service health check                           │
│  - GET /metrics: Emission statistics                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ Kafka Protocol
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│               Redpanda (Kafka-compatible)                       │
│                 localhost:9092                                  │
│  Topics:                                                        │
│  - market.lmp.raw         (LMP price ticks)                    │
│  - deal.events            (Trading deals)                      │
│  - nomination.events      (Energy scheduling)                  │
│  - iot.sensor.raw         (Sensor readings)                    │
│  - financial.price.raw    (Price ticks)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│            Bronze Consumer (Python + Delta Lake)                │
│          Reads Kafka, writes to SMB storage                     │
│                                                                 │
│  Partitioning strategy:                                         │
│  /Volumes/personal_folder/data/                                │
│  └── market_lmp_raw/                                            │
│      ├── asset_key=HB_NORTH/                                    │
│      │   ├── part-00000.parquet                                 │
│      │   └── _delta_log/                                        │
│      ├── asset_key=HB_SOUTH/                                    │
│      └── asset_key=HB_HOUSTON/                                  │
│  └── deal_events/                                               │
│      └── asset_key=DEAL-XXXXX/                                  │
│  └── iot_sensor_raw/                                            │
│      └── asset_key=SENSOR-XXXX/                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements
- Docker Desktop (with docker-compose)
- Node.js 18+ (for local development)
- 2GB free disk space (for Redpanda + SMB data)
- SMB share mounted at `/Volumes/personal_folder/data`

### Services Required
- ✅ Redpanda (Kafka broker)
- ✅ Producer API (FastAPI)
- ✅ Bronze Consumer (Python + Delta Lake)
- ✅ Generator Dashboard (React)

### Environment
```bash
cd /Users/vamshi/realtime-streaming-pipeline

# Verify SMB mount
ls /Volumes/personal_folder/data
# Should show: market_lmp_raw, deal_events, iot_sensor_raw, etc.

# Verify Docker
docker ps
docker-compose --version
```

---

## Starting the Pipeline

### 1. Start All Services

```bash
cd /Users/vamshi/realtime-streaming-pipeline

# Clean previous state (optional)
make down
rm -rf /Volumes/personal_folder/data/*

# Start all services
make up

# Verify health
make health
```

**Expected output:**
```
✅ redpanda: healthy
✅ producer: healthy
✅ generator: healthy
✅ bronze: ready
```

### 2. Verify Service Connectivity

```bash
# Check Producer API
curl http://localhost:8000/health
# { "status": "healthy", "kafka_connected": true }

# Check React app
curl http://localhost:5173
# Should return HTML

# Check Kafka topics
docker exec redpanda rpk topic list
# market.lmp.raw, deal.events, nomination.events, ...
```

### 3. Open Dashboard

```bash
# Open in browser
open http://localhost:5173

# Should see:
# - Synthetic Data Studio workspace
# - Customers table selected
# - 5 fields displayed
# - 2 blocking PII issues (email, date_of_birth)
# - "Run generation" button DISABLED (red)
```

---

## Testing the Full Pipeline

### Scenario 1: Load Dataset from API

**What happens:**
1. React app loads on startup
2. Makes GET request to http://localhost:8000/dataset
3. Receives dataset config (tables, fields, PII issues)
4. Displays in workspace

**Test it:**
```bash
# In browser console (F12)
console.log('API call should appear in Network tab')

# Check Producer logs
docker logs producer
# Should see: "GET /dataset" request

# Verify no errors in React console
# No red errors, only info logs
```

---

### Scenario 2: Configure PII Masking

**What happens:**
1. User clicks "Edit" button on email field
2. Changes PII masking strategy from "undefined" to "hash"
3. Configuration status updates to "complete"
4. Privacy warning disappears
5. "Run generation" button becomes ENABLED (blue)

**Test it manually in UI:**
1. Navigate to http://localhost:5173
2. Click edit icon on **email** field
3. Select masking strategy: "hash"
4. Click checkmark to save
5. Verify status badge changes to "complete" ✅
6. Repeat for **date_of_birth** field
7. Verify "Run generation" button now ENABLED
8. Verify privacy warning panel disappears

**Verify state:**
```bash
# Check browser console
# Should show no errors
# Generation button click ready
```

---

### Scenario 3: Generate Synthetic Data

**What happens:**
1. User clicks "Run generation" button
2. React POSTs to http://localhost:8000/emit/batch
3. Producer generates 1,000,000 customer events
4. Events sent to Kafka topic (market.lmp.raw, deal.events, etc.)
5. Bronze consumer reads from Kafka
6. Writes to SMB storage as Delta tables (partitioned by asset key)

**Test it:**
```bash
# 1. Click "Run generation" in browser
# Button should show spinner and be disabled

# 2. Check Producer logs
docker logs -f producer
# Should see: "Batch emitted X events to ..."

# 3. Watch Kafka messages
docker exec redpanda rpk topic consume market.lmp.raw --num 5
# Should see JSON events: delivery_node, lmp, event_time

# 4. Monitor Bronze consumer
docker logs -f bronze
# Should see: "Writing X events for asset_key=HB_NORTH"
# "Writing X events for asset_key=HB_SOUTH"
# "Writing X events for asset_key=HB_HOUSTON"

# 5. Check SMB storage
ls -la /Volumes/personal_folder/data/market_lmp_raw/
# Should see directories: asset_key=HB_NORTH, asset_key=HB_SOUTH, asset_key=HB_HOUSTON

# 6. Verify parquet files
ls /Volumes/personal_folder/data/market_lmp_raw/asset_key=HB_NORTH/
# Should see: part-00000.parquet, part-00001.parquet, ...
# _delta_log/ (versioning metadata)
```

---

## Verifying Data Flow

### Check Producer Metrics

```bash
# Get emission statistics
curl http://localhost:8000/metrics | jq
# {
#   "events_emitted_total": 1000000,
#   "events_emitted_by_topic": {
#     "market.lmp.raw": 1000000,
#     "deal.events": 0,
#     "nomination.events": 0
#   }
# }
```

### Check Kafka Messages

```bash
# Consumer from topic (first 10 messages)
docker exec redpanda rpk topic consume market.lmp.raw --num 10

# Should see JSON:
# {
#   "delivery_node": "HB_NORTH",
#   "lmp": 45.32,
#   "event_time": "2024-08-10T19:30:45.123456Z",
#   "ingest_time": "2024-08-10T19:30:45.123456Z"
# }
```

### Check Bronze Consumer Output

```bash
# View Delta table data
python3 << 'EOF'
from deltalake import DeltaTable
import pandas as pd

# Read all LMP data
dt = DeltaTable("/Volumes/personal_folder/data/market_lmp_raw")
df = dt.to_pandas()

print(f"Total rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print("\nFirst 5 rows:")
print(df.head())

# Read HB_NORTH partition only
dt_north = DeltaTable("/Volumes/personal_folder/data/market_lmp_raw/asset_key=HB_NORTH")
df_north = dt_north.to_pandas()
print(f"\nHB_NORTH rows: {len(df_north)}")
EOF
```

### Check SMB Disk Usage

```bash
# Estimate storage size
du -sh /Volumes/personal_folder/data/market_lmp_raw/
# Should show ~50-100MB for 1M rows

# Count total files
find /Volumes/personal_folder/data -name "*.parquet" | wc -l
# Should show multiple parquet files per partition
```

---

## Monitoring & Debugging

### Check All Logs

```bash
# Producer
docker logs producer | tail -20

# Bronze Consumer
docker logs bronze | tail -20

# Redpanda
docker logs redpanda | tail -20

# Generator (React app)
# Check browser console (F12)
```

### Service Health

```bash
# Full status
make health

# Individual checks
curl http://localhost:8000/health
curl http://localhost:5173/
docker exec redpanda rpk cluster info
```

### Performance Metrics

```bash
# Check emission rate
curl http://localhost:8000/metrics | jq '.events_emitted_total'

# Check Kafka lag
docker exec redpanda rpk group lag

# Check SMB write performance
time ls -R /Volumes/personal_folder/data/ | wc -l
```

---

## Common Issues & Troubleshooting

### Issue 1: React App Shows "Failed to fetch dataset"

**Symptoms:**
- Red error banner in React app
- Console shows: `Failed to fetch dataset`
- Mock data still displays

**Solution:**
```bash
# 1. Verify Producer is running
docker ps | grep producer
# Should show: producer container running

# 2. Check if Producer accepts requests
curl -v http://localhost:8000/dataset

# 3. Check Producer logs
docker logs producer | grep "ERROR"

# 4. Restart Producer
docker restart producer
```

### Issue 2: "Run generation" button stays disabled after configuring PII

**Symptoms:**
- Privacy warning still shows 2 issues
- Button remains gray

**Solution:**
```bash
# 1. Check browser console (F12)
# Look for TypeScript errors

# 2. Verify field updates were saved
# Fields should show "complete" status

# 3. Try refreshing page
# Cmd+Shift+R (hard refresh)

# 4. Check if masking strategy was actually saved
# Look at "Status" column - should be "complete" ✅
```

### Issue 3: Kafka messages not flowing to Bronze

**Symptoms:**
- No messages in Kafka consume
- No files written to SMB
- Bronze logs show "waiting for messages"

**Solution:**
```bash
# 1. Verify topics exist
docker exec redpanda rpk topic list

# 2. Check topic partition count
docker exec redpanda rpk topic describe market.lmp.raw

# 3. Reinitialize topics
docker exec rpk-init rpk topic delete market.lmp.raw || true
make up
```

### Issue 4: SMB mount not accessible

**Symptoms:**
- `ls /Volumes/personal_folder/data` returns "No such file or directory"
- Bronze consumer fails to write

**Solution:**
```bash
# 1. Check SMB mount status
mount | grep personal_folder
# Should show: smb://... on /Volumes/personal_folder/data

# 2. Remount if needed
umount /Volumes/personal_folder/data
# Use Finder to mount again, or:
mount_smbfs //user:password@server/share /Volumes/personal_folder/data

# 3. Verify write permissions
touch /Volumes/personal_folder/data/test.txt
rm /Volumes/personal_folder/data/test.txt
```

---

## API Endpoint Reference

### Producer API

#### GET /health
Health check endpoint.

```bash
curl http://localhost:8000/health
# { "status": "healthy", "kafka_connected": true }
```

#### GET /dataset
Returns dataset configuration for React UI.

```bash
curl http://localhost:8000/dataset | jq
# {
#   "id": "ds-ecommerce-001",
#   "name": "E-commerce Customer Orders",
#   "tables": [...],
#   "privacyIssues": [...]
# }
```

#### GET /metrics
Emission statistics.

```bash
curl http://localhost:8000/metrics | jq
# {
#   "events_emitted_total": 1000000,
#   "events_emitted_by_topic": {...}
# }
```

#### POST /emit/batch
Generate and emit events to Kafka.

```bash
curl -X POST http://localhost:8000/emit/batch \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "customer",
    "count": 1000000,
    "events": [],
    "frequency": "once",
    "constraints": {
      "seed": 42,
      "preserveNulls": true,
      "deterministicId": true
    }
  }' | jq

# {
#   "status": "success",
#   "topic": "market.lmp.raw",
#   "event_type": "customer",
#   "count": 1000000,
#   "frequency": "once"
# }
```

---

## Data Model Compatibility

### React UI Schema Field

```typescript
interface SchemaField {
  id: string
  fieldName: string
  dataType: 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'timestamp'
  nullable: boolean
  generatorType: string
  distribution?: string
  piiLabel?: 'email' | 'phone' | 'ssn' | 'dob' | 'address'
  piiMaskingStrategy?: 'hash' | 'encrypt' | 'generalize' | 'synthetic'
  relationshipTarget?: string
  configurationStatus: 'complete' | 'partial' | 'blocked'
}
```

### Producer API Response

The /dataset endpoint returns the same structure, allowing React to work seamlessly.

---

## Performance Tuning

### Emission Rate

Adjust Producer emission rate in `.env`:

```bash
PRODUCER_EMIT_RATE=1.0  # Events per second
# Increase for faster emission: 10.0
# Decrease for slower emission: 0.1
```

### Batch Size

Adjust Bronze batch size in `bronze/consumer.py`:

```python
BATCH_SIZE = 5  # Events per write
# Increase for fewer, larger writes: 100
# Decrease for more, smaller writes: 1
```

### Kafka Partitions

Adjust partition count in `docker-compose.yml`:

```env
REDPANDA_PARTITIONS=3  # Number of partitions
# Increase for parallelism: 12
```

---

## Next Steps

### Short-term (Testing)
1. ✅ Test dataset loading from API
2. ✅ Configure PII masking manually
3. ✅ Trigger one generation job
4. ✅ Verify data on SMB

### Medium-term (Enhancement)
- [ ] Add real-time progress updates (WebSocket)
- [ ] Implement data preview (sample 5–10 rows)
- [ ] Add quality metrics (statistical similarity)
- [ ] Schedule recurring generation jobs
- [ ] Export to CSV, Parquet, Delta

### Long-term (Scaling)
- [ ] Multi-workspace support
- [ ] Team collaboration (comments, approvals)
- [ ] Performance profiling dashboard
- [ ] Advanced analytics on generated data
- [ ] Integration with dbt for transformations

---

## Summary

✅ **End-to-end pipeline is ready:**
1. React UI loads dataset from Producer API
2. Users configure PII masking strategies
3. Click "Run generation" to emit events to Kafka
4. Bronze consumer reads from Kafka
5. Writes to SMB storage as versioned Delta tables

**Status**: Production-ready  
**Date**: 2024-08-10  
**Maintained by**: Synthetic Data Studio Team
