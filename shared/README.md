# Shared Event Schemas

Centralized schema definitions for all Kafka topics in the streaming pipeline.

## Structure

```
shared/
├── schemas.py           # Pydantic models + JSON schemas
├── topics.py            # Topic configuration
├── generate_schemas.py  # Export schemas to JSON
└── README.md            # This file
```

## Event Types

### 1. LmpTick (market.lmp.raw)
Market LMP (Locational Marginal Price) ticks from ERCOT power market.

**Fields:**
- `delivery_node` (str): ERCOT delivery node (e.g., HB_NORTH, HB_SOUTH)
- `lmp` (float): LMP price in $/MWh
- `event_time` (str): Business timestamp (ISO 8601)
- `ingest_time` (str): When event was received

**Example:**
```json
{
  "delivery_node": "HB_NORTH",
  "lmp": 45.50,
  "event_time": "2026-08-10T23:12:45.404530",
  "ingest_time": "2026-08-10T23:12:45.404545"
}
```

### 2. DealEvent (deal.events)
Power trading deal events (NEW, AMENDED, CANCELLED).

**Fields:**
- `deal_id` (str): Unique deal identifier
- `event_type` (str): NEW | AMENDED | CANCELLED
- `volume_mw` (float): Trade volume in MW
- `counterparty` (str): Trading partner name
- `event_time` (str): Business timestamp
- `ingest_time` (str): Ingest timestamp

**Example:**
```json
{
  "deal_id": "DEAL-001",
  "event_type": "NEW",
  "volume_mw": 100.0,
  "counterparty": "COUNTERPARTY-A",
  "event_time": "2026-08-10T23:12:45.404530",
  "ingest_time": "2026-08-10T23:12:45.404545"
}
```

### 3. NominationEvent (nomination.events)
Energy scheduling nominations and amendments.

**Fields:**
- `nomination_id` (str): Unique nomination ID
- `deal_id` (str): Reference to deal
- `status` (str): PENDING | CONFIRMED | REJECTED | AMENDED
- `volume_mw` (float): Nominated volume
- `settlement_period` (str): HE01-HE24
- `event_time` (str): Business timestamp
- `ingest_time` (str): Ingest timestamp

**Example:**
```json
{
  "nomination_id": "NOM-001",
  "deal_id": "DEAL-001",
  "status": "CONFIRMED",
  "volume_mw": 100.0,
  "settlement_period": "HE01",
  "event_time": "2026-08-10T23:12:45.404530",
  "ingest_time": "2026-08-10T23:12:45.404545"
}
```

## Usage

### In Python

```python
from shared.schemas import LmpTick, DealEvent, validate_event

# Create event (validates automatically)
lmp = LmpTick(
    delivery_node="HB_NORTH",
    lmp=45.50
)

# Validate raw dict
payload = {"delivery_node": "HB_SOUTH", "lmp": 42.0}
is_valid = validate_event("market.lmp.raw", payload)
```

### Print all schemas

```bash
cd shared
python generate_schemas.py
```

Exports JSON schemas to `shared/schemas_json/` directory.

## Topic Configuration

- **market.lmp.raw**: 3 partitions, 1-day retention
- **deal.events**: 3 partitions, 7-day retention
- **nomination.events**: 3 partitions, 7-day retention

Partitions are keyed by entity:
- LMP: keyed by `delivery_node` (same node → same partition)
- Deals: keyed by `deal_id` (same deal → same partition)
- Nominations: keyed by `nomination_id`

This ensures ordering within each entity while enabling parallelism.

## Schema Evolution

To add a new event type:

1. **Add Pydantic model** to `schemas.py`
2. **Add to SCHEMAS dict** in `schemas.py`
3. **Add TopicConfig** to `topics.py`
4. **Regenerate schemas**: `python generate_schemas.py`

Example:

```python
# schemas.py
class NewEventType(BaseModel):
    field1: str
    field2: float

SCHEMAS["new.topic"] = NewEventType.model_json_schema()

# topics.py
TOPICS["new.topic"] = TopicConfig(
    name="new.topic",
    partitions=3,
    description="New event type"
)
```

## Validation in Producer

The Producer uses these schemas to validate events before emission:

```python
from shared.schemas import LmpTick

@app.post("/emit/lmp")
async def emit_lmp(lmp: LmpTick):  # Auto-validates
    await kafka_producer.send_and_wait(
        "market.lmp.raw",
        value=lmp.model_dump(),
        key=lmp.delivery_node.encode()
    )
```

## Validation in Bronze

Bronze stores raw events and metadata:

```python
# Raw payload stored as-is in Delta
data = {
    "_raw_payload": [json.dumps(msg) for msg in messages],
    "_kafka_offset": [...],
    "_kafka_partition": [...],
    "_ingest_ts": [...]
}
```

Downstream systems (queries, aggregations) can parse and validate.

## JSON Schema Export

Run to export schemas:

```bash
cd shared
python generate_schemas.py
```

Creates:
- `schemas_json/market_lmp_raw.json`
- `schemas_json/deal_events.json`
- `schemas_json/nomination_events.json`

Use these for API documentation, data validation, or downstream systems.
