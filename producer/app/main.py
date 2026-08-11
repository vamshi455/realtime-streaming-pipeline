import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer

# Configuration
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092").split(",")
PRODUCER_LOG_LEVEL = os.getenv("PRODUCER_LOG_LEVEL", "INFO")
EMIT_RATE = float(os.getenv("PRODUCER_EMIT_RATE", "1"))

TOPIC_LMP = os.getenv("KAFKA_TOPIC_LMP", "market.lmp.raw")
TOPIC_DEALS = os.getenv("KAFKA_TOPIC_DEALS", "deal.events")
TOPIC_NOMINATIONS = os.getenv("KAFKA_TOPIC_NOMINATIONS", "nomination.events")

# Logging
logging.basicConfig(level=PRODUCER_LOG_LEVEL)
logger = logging.getLogger(__name__)

# FastAPI
app = FastAPI(title="Event Producer", version="1.0.0")

# Global Kafka producer
kafka_producer: Optional[AIOKafkaProducer] = None

# Metrics (in-memory, reset on restart)
metrics = {
    "events_emitted_total": 0,
    "events_emitted_by_topic": {
        TOPIC_LMP: 0,
        TOPIC_DEALS: 0,
        TOPIC_NOMINATIONS: 0,
    },
}


# Pydantic Models
class LmpTick(BaseModel):
    delivery_node: str
    lmp: float
    event_time: Optional[str] = None


class DealEvent(BaseModel):
    deal_id: str
    event_type: str  # NEW, AMENDED, CANCELLED
    volume_mw: float
    event_time: Optional[str] = None


class NominationEvent(BaseModel):
    nomination_id: str
    deal_id: str
    status: str
    event_time: Optional[str] = None


class BatchEmitRequest(BaseModel):
    """Batch emit request from generator"""
    event_type: str
    count: int
    events: List[Dict[str, Any]]
    frequency: Optional[str] = "Once"
    constraints: Optional[Dict] = None
    timestamp: Optional[str] = None


# Startup / Shutdown
@app.on_event("startup")
async def startup():
    global kafka_producer
    logger.info(f"Connecting to Kafka brokers: {KAFKA_BROKERS}")
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BROKERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await kafka_producer.start()
    logger.info("Kafka producer started")


@app.on_event("shutdown")
async def shutdown():
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Kafka producer stopped")


# Health & Metrics
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "kafka_connected": kafka_producer is not None and not kafka_producer._closed,
    }


@app.get("/metrics")
async def get_metrics():
    return metrics


# Event Emission Endpoints
@app.post("/emit/lmp")
async def emit_lmp(lmp: LmpTick):
    """Emit an LMP price tick"""
    if not kafka_producer or kafka_producer._closed:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    event_time = lmp.event_time or datetime.utcnow().isoformat()
    message = {
        "delivery_node": lmp.delivery_node,
        "lmp": lmp.lmp,
        "event_time": event_time,
        "ingest_time": datetime.utcnow().isoformat(),
    }

    try:
        await kafka_producer.send_and_wait(TOPIC_LMP, value=message, key=lmp.delivery_node.encode())
        metrics["events_emitted_total"] += 1
        metrics["events_emitted_by_topic"][TOPIC_LMP] += 1
        logger.info(f"Emitted LMP: {lmp.delivery_node} @ {event_time}")
        return {"status": "emitted", "topic": TOPIC_LMP, "message": message}
    except Exception as e:
        logger.error(f"Failed to emit LMP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emit/deal")
async def emit_deal(deal: DealEvent):
    """Emit a deal event"""
    if not kafka_producer or kafka_producer._closed:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    event_time = deal.event_time or datetime.utcnow().isoformat()
    message = {
        "deal_id": deal.deal_id,
        "event_type": deal.event_type,
        "volume_mw": deal.volume_mw,
        "event_time": event_time,
        "ingest_time": datetime.utcnow().isoformat(),
    }

    try:
        await kafka_producer.send_and_wait(TOPIC_DEALS, value=message, key=deal.deal_id.encode())
        metrics["events_emitted_total"] += 1
        metrics["events_emitted_by_topic"][TOPIC_DEALS] += 1
        logger.info(f"Emitted Deal: {deal.deal_id} ({deal.event_type})")
        return {"status": "emitted", "topic": TOPIC_DEALS, "message": message}
    except Exception as e:
        logger.error(f"Failed to emit deal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emit/nomination")
async def emit_nomination(nom: NominationEvent):
    """Emit a nomination event"""
    if not kafka_producer or kafka_producer._closed:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    event_time = nom.event_time or datetime.utcnow().isoformat()
    message = {
        "nomination_id": nom.nomination_id,
        "deal_id": nom.deal_id,
        "status": nom.status,
        "event_time": event_time,
        "ingest_time": datetime.utcnow().isoformat(),
    }

    try:
        await kafka_producer.send_and_wait(TOPIC_NOMINATIONS, value=message, key=nom.nomination_id.encode())
        metrics["events_emitted_total"] += 1
        metrics["events_emitted_by_topic"][TOPIC_NOMINATIONS] += 1
        logger.info(f"Emitted Nomination: {nom.nomination_id}")
        return {"status": "emitted", "topic": TOPIC_NOMINATIONS, "message": message}
    except Exception as e:
        logger.error(f"Failed to emit nomination: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch Emit: From Synthetic Data Generator
@app.post("/emit/batch")
async def emit_batch(request: BatchEmitRequest):
    """
    Emit batch of pre-generated events to Kafka.
    Used by Synthetic Data Generator dashboard.
    """
    if not kafka_producer or kafka_producer._closed:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    event_type = request.event_type
    events = request.events
    frequency = request.frequency or "Once"

    # Map event_type to topic
    topic_map = {
        "lmp_tick": TOPIC_LMP,
        "deal_event": TOPIC_DEALS,
        "nomination_event": TOPIC_NOMINATIONS,
        "iot_sensor": "iot.sensor.raw",
        "financial_price": "financial.price.raw",
    }

    topic = topic_map.get(event_type)
    if not topic:
        raise HTTPException(status_code=400, detail=f"Unknown event_type: {event_type}")

    try:
        emitted = 0
        for event in events:
            # Determine key for partitioning
            if event_type == "lmp_tick":
                key = event.get("delivery_node", "unknown").encode()
            elif event_type == "deal_event":
                key = event.get("deal_id", "unknown").encode()
            elif event_type == "nomination_event":
                key = event.get("nomination_id", "unknown").encode()
            elif event_type == "iot_sensor":
                key = event.get("sensor_id", "unknown").encode()
            elif event_type == "financial_price":
                key = event.get("symbol", "unknown").encode()
            else:
                key = b"default"

            await kafka_producer.send_and_wait(topic, value=event, key=key)
            emitted += 1

        metrics["events_emitted_total"] += emitted
        metrics["events_emitted_by_topic"][topic] = metrics["events_emitted_by_topic"].get(topic, 0) + emitted

        logger.info(
            f"Batch emitted {emitted} {event_type} events to {topic} "
            f"(frequency: {frequency})"
        )

        return {
            "status": "success",
            "topic": topic,
            "event_type": event_type,
            "count": emitted,
            "frequency": frequency,
        }

    except Exception as e:
        logger.error(f"Failed to emit batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Scenario: Emit a burst of events
@app.post("/scenarios/baseline")
async def scenario_baseline(count: int = 10):
    """Emit a baseline scenario: steady stream of LMP ticks"""
    if not kafka_producer or kafka_producer._closed:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    nodes = ["HB_NORTH", "HB_SOUTH", "HB_HOUSTON"]
    emitted = 0

    try:
        for i in range(count):
            for node in nodes:
                lmp_value = 40.0 + (i % 10)
                message = {
                    "delivery_node": node,
                    "lmp": lmp_value,
                    "event_time": datetime.utcnow().isoformat(),
                    "ingest_time": datetime.utcnow().isoformat(),
                }
                await kafka_producer.send_and_wait(TOPIC_LMP, value=message, key=node.encode())
                metrics["events_emitted_total"] += 1
                metrics["events_emitted_by_topic"][TOPIC_LMP] += 1
                emitted += 1
            await asyncio.sleep(0.1)  # Throttle

        logger.info(f"Baseline scenario emitted {emitted} events")
        return {"status": "completed", "events_emitted": emitted}
    except Exception as e:
        logger.error(f"Baseline scenario failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
