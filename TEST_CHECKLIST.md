# End-to-End Testing Checklist

Comprehensive test plan for the Synthetic Data Studio pipeline integration.

## Pre-Flight Checks

- [ ] SMB share mounted at `/Volumes/personal_folder/data`
- [ ] Docker Desktop running and healthy
- [ ] Node.js 18+ installed (`node --version`)
- [ ] All services stopped from previous runs (`make down`)
- [ ] Clean SMB directory (`rm -rf /Volumes/personal_folder/data/*`)
- [ ] Network connectivity to localhost ports 5173, 8000, 9092

---

## Infrastructure Setup

### Docker Compose Services

- [ ] **Redpanda (Kafka)**
  - [ ] Container running: `docker ps | grep redpanda`
  - [ ] Health check passing: `curl http://localhost:9644/v1/status/ready`
  - [ ] Topics created: `docker exec redpanda rpk topic list` shows `market.lmp.raw`

- [ ] **Producer (FastAPI)**
  - [ ] Container running: `docker ps | grep producer`
  - [ ] Health endpoint: `curl http://localhost:8000/health` returns `{"status": "healthy"}`
  - [ ] Kafka connected: response includes `"kafka_connected": true`
  - [ ] API accessible: `curl http://localhost:8000/dataset` returns JSON

- [ ] **Generator (React)**
  - [ ] Container running: `docker ps | grep generator`
  - [ ] Accessible: `curl http://localhost:5173` returns HTML
  - [ ] No 502 errors: check browser console (F12)

- [ ] **Bronze Consumer (Python)**
  - [ ] Container running: `docker ps | grep bronze`
  - [ ] Logs show: "Kafka consumer started"
  - [ ] No errors in `docker logs bronze | grep ERROR`
  - [ ] Ready to write to SMB: `/Volumes/personal_folder/data` exists and writable

**Command:**
```bash
make up
make health
```

---

## UI/UX Tests (React Dashboard)

### 1. Dashboard Loads Successfully

- [ ] **Page load** (http://localhost:5173)
  - [ ] No blank screen or loading spinner hanging >5 seconds
  - [ ] Logo/title visible: "Synthetic Data Studio"
  - [ ] Three-panel layout renders: Left, Center, Right

- [ ] **Error handling**
  - [ ] If API unavailable: Shows red error banner, falls back to mock data
  - [ ] If API available: No error banners, clean layout
  - [ ] Console clean: No red errors in F12 console

### 2. Dataset Loads from API

- [ ] **GET /dataset request**
  - [ ] Network tab (F12) shows request to `http://localhost:8000/dataset`
  - [ ] Response status: 200
  - [ ] Response time: <500ms

- [ ] **Data displays correctly**
  - [ ] Dataset name: "E-commerce Customer Orders"
  - [ ] Tables loaded: Customers, Orders, Order Items
  - [ ] Configuration: "92% complete"
  - [ ] Privacy issues: 2 blocking issues visible

### 3. Left Panel (Dataset Navigation)

- [ ] **Metadata displays**
  - [ ] Dataset name, description, source visible
  - [ ] Modified date shows current date
  - [ ] Configuration progress bar at 92%

- [ ] **Table selector works**
  - [ ] "Customers" table highlighted by default
  - [ ] Clicking "Orders" highlights it and updates center panel
  - [ ] Clicking "Order Items" highlights it and updates center panel
  - [ ] Field count updates: Customers (5), Orders (5), Order Items (5)

- [ ] **Status footer**
  - [ ] Configuration badge shows "92%"
  - [ ] Issues count shows "⚠️ 2 issues"

### 4. Center Panel (Schema Editor)

- [ ] **Search functionality**
  - [ ] Type "email" in search box: filters to 1 field
  - [ ] Type "customer" in search box: filters to 2 fields (customer_id, foreign key)
  - [ ] Clear search: all 5 fields display again

- [ ] **Column visibility toggle**
  - [ ] Toggle "Type" column: visibility changes icon (👁️/🚫)
  - [ ] Column hides/shows in table
  - [ ] Works for all columns: Field Name, Type, Generator, PII, Null?, Relationship, Status

- [ ] **Schema table displays**
  - [ ] All 5 Customers fields visible: customer_id, email, date_of_birth, country, created_at
  - [ ] Column headers: Field Name, Type, Generator, PII, Nullable, Relationship, Status, Action
  - [ ] Status badges show correctly:
    - customer_id: ✅ complete
    - email: ❌ blocked (red)
    - date_of_birth: ❌ blocked (red)
    - country: ✅ complete
    - created_at: ✅ complete

### 5. Privacy Warning Panel

- [ ] **Panel displays** (top of center panel, above schema table)
  - [ ] Red background with red left border
  - [ ] Icon: ⚠️
  - [ ] Title: "2 issues blocking generation"
  - [ ] Subtitle: "PII fields require masking strategy. Update in Schema tab."

- [ ] **Issue list**
  - [ ] Shows **email** with "Configure →" button
  - [ ] Shows **date_of_birth** with "Configure →" button
  - [ ] Button click scrolls/focuses to field in table

### 6. Edit PII Masking Strategy

- [ ] **Click edit on email field**
  - [ ] Edit icon (✎) appears on status column
  - [ ] Click it: row highlights with accent background
  - [ ] Edit controls appear: dropdown for masking strategy

- [ ] **Select masking strategy**
  - [ ] Dropdown shows options: hash, encrypt, generalize, synthetic
  - [ ] Select "hash"
  - [ ] Save changes (checkmark button)

- [ ] **Status updates**
  - [ ] Row un-highlights
  - [ ] Status badge changes from "blocked" (red) to "complete" (green)
  - [ ] Privacy warning panel updates (one fewer issue)

- [ ] **Repeat for date_of_birth**
  - [ ] Click edit, select "generalize" masking strategy
  - [ ] Save changes
  - [ ] Status updates to "complete" (green)

- [ ] **Privacy warning disappears**
  - [ ] After both fields configured, warning panel vanishes
  - [ ] Right panel updates

---

## Right Panel (Generation Config)

### After Configuring PII (2/2 issues resolved)

- [ ] **Target Rows**
  - [ ] Shows: "1,000,000"
  - [ ] Progress bar filled 100%

- [ ] **Deterministic Seed**
  - [ ] Shows: "⚡ 42"
  - [ ] In monospaced font
  - [ ] Copy button ready (future feature)

- [ ] **Estimated Runtime**
  - [ ] Shows: "4 min"
  - [ ] Text explains: "~4 minutes at 1M rows/min"

- [ ] **Configuration Status**
  - [ ] Progress bar at 92% (with blue fill)
  - [ ] Shows: "92%"
  - [ ] Text: "8% incomplete" (or similar)

- [ ] **Status checklist**
  - [ ] Green panel appears: ✓ "Ready to generate"
  - [ ] Text: "All configuration requirements met"
  - [ ] No red error panel

- [ ] **Generate button state**
  - [ ] Top bar button: "▶ Run generation"
  - [ ] Background color: Blue (enabled)
  - [ ] Hover state: Darker blue
  - [ ] NOT disabled (no gray overlay)

---

## Generation Flow

### Trigger Generation

- [ ] **Click "Run generation" button**
  - [ ] Button shows spinner (animated rotation)
  - [ ] Button text changes to loading state
  - [ ] Button disabled during generation
  - [ ] Cannot click again

- [ ] **Monitor Producer logs**
  ```bash
  docker logs -f producer
  # Should see: "Batch emitted X events to market.lmp.raw"
  ```

- [ ] **Check Kafka messages**
  ```bash
  docker exec redpanda rpk topic consume market.lmp.raw --num 3
  # Should see JSON events with fields:
  # - delivery_node
  # - lmp (numeric value)
  # - event_time
  # - ingest_time
  ```

### Wait for Completion

- [ ] **Generation completes** (~2-5 seconds for mock data)
  - [ ] Button spinner stops
  - [ ] Button becomes clickable again
  - [ ] No error messages in console

### Verify Data Flow to SMB

- [ ] **Check SMB directory structure**
  ```bash
  ls -la /Volumes/personal_folder/data/
  # Should show directories for topics
  ```

- [ ] **Check parquet files**
  ```bash
  ls /Volumes/personal_folder/data/market_lmp_raw/
  # Should show: asset_key=HB_NORTH, asset_key=HB_SOUTH, asset_key=HB_HOUSTON
  ```

- [ ] **Check Delta table metadata**
  ```bash
  ls /Volumes/personal_folder/data/market_lmp_raw/asset_key=HB_NORTH/
  # Should show: part-00000.parquet, _delta_log/
  ```

- [ ] **Read and verify data**
  ```python
  from deltalake import DeltaTable
  dt = DeltaTable("/Volumes/personal_folder/data/market_lmp_raw")
  df = dt.to_pandas()
  
  # Should succeed without errors
  # df.shape should show > 0 rows
  ```

---

## API Endpoint Tests

### GET /health

```bash
curl http://localhost:8000/health
# Expected:
# {
#   "status": "healthy",
#   "kafka_connected": true
# }
```

- [ ] Status is "healthy"
- [ ] kafka_connected is true

### GET /dataset

```bash
curl http://localhost:8000/dataset | jq '.tables[0].fields[0]'
# Expected: customer_id field with all properties
```

- [ ] Response is valid JSON
- [ ] Contains "tables" array with 1+ tables
- [ ] First table is "customers"
- [ ] Has fields array with 5 fields
- [ ] First field is "customer_id"
- [ ] Has all required properties: fieldName, dataType, generatorType, configurationStatus

### GET /metrics

```bash
curl http://localhost:8000/metrics | jq '.events_emitted_total'
# Expected: integer > 0 after generation
```

- [ ] Response is valid JSON
- [ ] Contains "events_emitted_total"
- [ ] Contains "events_emitted_by_topic"
- [ ] After generation, counts increase

### POST /emit/batch

```bash
curl -X POST http://localhost:8000/emit/batch \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "customer",
    "count": 1000,
    "events": [],
    "frequency": "once"
  }' | jq '.status'
# Expected: "success"
```

- [ ] Request accepted with 200 status
- [ ] Response has "status": "success"
- [ ] Response has "topic", "event_type", "count"

---

## Performance & Scalability Tests

### Emission Rate

- [ ] **1,000,000 row generation**
  - [ ] Completes in <5 minutes
  - [ ] Producer CPU: <50%
  - [ ] Memory stable (no leaks)
  - [ ] Kafka throughput: >50K msg/sec

### Bronze Consumer

- [ ] **Data written to SMB**
  - [ ] No write errors in logs
  - [ ] Files created in correct partition directories
  - [ ] Parquet files are valid (readable by pandas)
  - [ ] Delta Lake versioning works (_delta_log present)

### React Performance

- [ ] **UI responsiveness**
  - [ ] Schema table scrolls smoothly (dense 100+ fields)
  - [ ] Search filters results in <100ms
  - [ ] Column toggle works instantly
  - [ ] No lag during generation spinner animation

---

## Error Scenarios

### Scenario 1: Producer API Unavailable

**Setup:** Stop producer before loading React app

```bash
docker stop producer
# Load http://localhost:5173
```

- [ ] Red error banner shows: "API Connection Warning"
- [ ] Message: "Failed to connect" or similar
- [ ] App still usable with mock data
- [ ] No unhandled JS errors
- [ ] "Run generation" button attempts API call (fails gracefully)

**Recovery:**
```bash
docker start producer
# Refresh page
```

- [ ] Error banner disappears
- [ ] Real data loads from API

### Scenario 2: Kafka Broker Unavailable

**Setup:** Stop Redpanda

```bash
docker stop redpanda
# Try to generate
```

- [ ] "Run generation" button triggers POST to Producer
- [ ] Producer fails to send to Kafka (expected)
- [ ] Error message appears in React (production: WebSocket or polling)
- [ ] Bronze consumer gracefully waits (doesn't crash)

**Recovery:**
```bash
docker start redpanda
# Try generation again
```

- [ ] Services reconnect
- [ ] Generation completes

### Scenario 3: SMB Mount Unmounted

**Setup:** Unmount SMB

```bash
umount /Volumes/personal_folder/data
# Try to generate
```

- [ ] Producer generates events (OK)
- [ ] Events go to Kafka (OK)
- [ ] Bronze consumer fails to write (expected)
- [ ] No crash, logs show filesystem error

**Recovery:**
```bash
# Remount SMB
# Try generation again
```

- [ ] Data writes successfully

---

## Browser & Compatibility Tests

### Chrome

- [ ] [ ] Page loads without errors
- [ ] [ ] Console shows no errors (F12)
- [ ] [ ] All UI elements visible and styled correctly
- [ ] [ ] Search box responsive and clear
- [ ] [ ] Dropdowns work

### Safari

- [ ] [ ] Page loads
- [ ] [ ] Styling consistent with Chrome
- [ ] [ ] Touch interactions work (if on Mac trackpad)

### Firefox

- [ ] [ ] Page loads
- [ ] [ ] Developer tools (F12) show no errors
- [ ] [ ] Performance similar to Chrome

---

## Documentation & Deployment

- [ ] README.md in dashboard/ is accurate
- [ ] REACT_SETUP.md covers all setup steps
- [ ] INTEGRATION_GUIDE.md has complete API reference
- [ ] Docker healthchecks all passing
- [ ] No uncommitted changes in git
- [ ] All commits pushed to GitHub

---

## Final Sign-Off

**Test Date:** _______________  
**Tester Name:** _______________  
**All Tests Passed:** ☐ Yes ☐ No (explain any failures)

**Issues Found:** (list any blockers or nice-to-haves)

1. _______________
2. _______________
3. _______________

**Sign-Off:** _______________

---

## Quick Reference: Commands

```bash
# Start everything
make up

# Check health
make health

# View logs
make logs

# Stop everything
make down

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/dataset | jq
curl http://localhost:8000/metrics | jq

# Check Kafka
docker exec redpanda rpk topic list
docker exec redpanda rpk topic consume market.lmp.raw --num 5

# Check SMB
ls -la /Volumes/personal_folder/data/
find /Volumes/personal_folder/data -name "*.parquet" | wc -l

# React development
cd dashboard
npm run dev

# React build
npm run build
npm run preview
```

---

**Status**: ✅ Ready for testing  
**Date**: 2024-08-10
