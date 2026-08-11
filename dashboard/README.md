# Synthetic Data Generator Dashboard

Interactive Streamlit app for generating and emitting synthetic data to Kafka.

**Use cases:**
- Testing streaming pipelines with realistic data
- Learning Kafka and event processing
- Benchmarking systems with high-volume data
- Multi-domain data generation (power, IoT, finance, etc.)

## Features

### 1. Quick Generate (Natural Language)
Type what you want, the app parses it:
```
"Generate 100 LMP ticks for HB_NORTH between 40 and 50"
"Create 50 deal events with volumes 100-500"
"500 IoT sensor readings for temperature 20-30°C"
```

### 2. Advanced Generator
- Select event type (LMP, deals, nominations, sensors, prices)
- Configure count, ranges, constraints
- Choose frequency (once, every 1 min, etc.)

### 3. Preview
- Generate and preview data
- View as JSON or table
- Export as CSV

### 4. Status & Monitoring
- Check producer health
- View emission metrics
- Monitor event counts

## Running

### Start all services
```bash
make down
docker compose build generator
make up
```

### Access dashboard
```
http://localhost:8501
```

## Supported Event Types

### Power Trading
- **lmp_tick**: Market prices (LMP), keyed by delivery_node
- **deal_event**: Trading deals (NEW, AMENDED, CANCELLED), keyed by deal_id
- **nomination_event**: Energy scheduling confirmations, keyed by nomination_id

### IoT
- **iot_sensor**: Temperature, humidity, pressure readings from sensors

### Finance
- **financial_price**: Stock/commodity price ticks

## Data Flow

```
Streamlit Dashboard
  ↓ (user clicks "Generate & Emit")
  ↓ (sends POST /emit/batch with events)
Producer (FastAPI)
  ↓ (sends to Kafka topics)
Kafka (Redpanda)
  ↓
Bronze Consumer (reads from Kafka)
  ↓
SMB Shared Drive (/Volumes/personal_folder/data/)
  └── organized by asset_key (delivery_node, deal_id, etc.)
```

## Example: Generate LMP Ticks

**Quick way:**
```
Enter: "Generate 100 LMP ticks for HB_NORTH between 40 and 50"
Click: "Generate & Emit"
Result: 100 events sent to Kafka, stored on SMB
```

**Advanced way:**
1. Event Type: `lmp_tick`
2. Count: `100`
3. LMP Range: `40.0` to `50.0`
4. Nodes: `HB_NORTH` (uncheck others)
5. Click: "Generate & Emit"

## Example: IoT Sensor Data

**Quick way:**
```
Enter: "1000 temperature sensor readings 20-30°C in New York"
```

**Advanced way:**
1. Event Type: `iot_sensor`
2. Count: `1000`
3. Value Range: `20.0` to `30.0`
4. Sensor Type: `temperature`
5. Location: `New York`
6. Click: "Generate & Emit"

## Natural Language Parsing

The app extracts:
- **Count**: "100 LMP" → count=100
- **Event type**: "LMP ticks" → lmp_tick
- **Ranges**: "between 40 and 50" → (40, 50)
- **Location/Node**: "for HB_NORTH" → nodes=[HB_NORTH]

Supports phrases like:
- "Generate X events"
- "Create X deals"
- "Emit X readings"
- "between A and B"
- "from A to B"
- "for/at LOCATION"

## Data Generation

Uses **Faker** library for realistic data:
- Company names (counterparties)
- Cities (sensor locations)
- Random numeric ranges
- Timestamps

Each event includes:
- Business data (lmp, volume, status, etc.)
- Timestamps (event_time, ingest_time)
- Unique IDs (deal_id, nomination_id, sensor_id, etc.)

## Scheduling (Future)

Planned features:
- [ ] Schedule recurring generation (every 1 min, hourly, etc.)
- [ ] Pause/resume jobs
- [ ] View active generation jobs
- [ ] APScheduler backend integration

## Output on SMB

After emitting, data is organized by asset:
```
/Volumes/personal_folder/data/
├── market_lmp_raw/
│   ├── asset_key=HB_NORTH/
│   │   ├── part-00000.parquet
│   │   └── _delta_log/
│   ├── asset_key=HB_SOUTH/
│   └── asset_key=HB_HOUSTON/
├── deal_events/
│   ├── asset_key=DEAL-12345/
│   └── ...
└── iot_sensor_raw/
    ├── asset_key=SENSOR-1001/
    └── ...
```

## Query Generated Data

```python
from deltalake import DeltaTable
import pandas as pd

# Read all LMP data
dt = DeltaTable("/Volumes/personal_folder/data/market_lmp_raw")
df = dt.to_pandas()

# Read just HB_NORTH
dt_north = DeltaTable(
    "/Volumes/personal_folder/data/market_lmp_raw/asset_key=HB_NORTH"
)
df_north = dt_north.to_pandas()

print(df_north.head())
```

## Monitoring

Check producer metrics:
- Total events emitted
- Events per topic
- API health status

From dashboard: Click "Get Metrics" button

Or via curl:
```bash
curl http://localhost:8000/metrics | jq
```

## Architecture

- **Frontend**: Streamlit (Python web app)
- **Backend**: FastAPI Producer with `/emit/batch` endpoint
- **Message Bus**: Kafka (Redpanda)
- **Consumer**: Bronze (reads Kafka → writes to SMB as Delta tables)
- **Storage**: SMB shared drive with asset-based partitioning

## For Learning

This dashboard teaches:
- Event schema design
- Kafka producer patterns
- Natural language parsing
- Streaming data pipelines
- Delta Lake partitioning
- Synthetic data generation

Run scenarios, modify constraints, monitor the end-to-end flow.

## Notes

- **Testing only**: For benchmarking, learning, demo purposes
- **No validation**: Generated data is synthetic, not validated for domain correctness
- **Volume limits**: Test with up to ~1M events before checking SMB disk space
- **Performance**: Adjust batch sizes and emit frequency based on system capacity

Start generating! 🚀
