"""Event schemas for all Kafka topics"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import json


class LmpTick(BaseModel):
    """Market LMP (Locational Marginal Price) tick"""
    delivery_node: str = Field(..., description="ERCOT delivery node (e.g., HB_NORTH)")
    lmp: float = Field(..., description="LMP price in $/MWh")
    event_time: Optional[str] = Field(None, description="Business timestamp (ISO 8601)")
    ingest_time: Optional[str] = Field(None, description="Ingest timestamp (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "delivery_node": "HB_NORTH",
                "lmp": 45.50,
                "event_time": "2026-08-10T23:12:45.404530",
                "ingest_time": "2026-08-10T23:12:45.404545"
            }
        }


class DealEvent(BaseModel):
    """Power trading deal event"""
    deal_id: str = Field(..., description="Unique deal identifier")
    event_type: str = Field(..., description="Event type: NEW, AMENDED, CANCELLED")
    volume_mw: float = Field(..., description="Trade volume in MW")
    counterparty: Optional[str] = Field(None, description="Trading counterparty")
    event_time: Optional[str] = Field(None, description="Business timestamp (ISO 8601)")
    ingest_time: Optional[str] = Field(None, description="Ingest timestamp (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "deal_id": "DEAL-001",
                "event_type": "NEW",
                "volume_mw": 100.0,
                "counterparty": "COUNTERPARTY-A",
                "event_time": "2026-08-10T23:12:45.404530",
                "ingest_time": "2026-08-10T23:12:45.404545"
            }
        }


class NominationEvent(BaseModel):
    """Nomination event (energy scheduling confirmation)"""
    nomination_id: str = Field(..., description="Unique nomination identifier")
    deal_id: str = Field(..., description="Reference to deal_id")
    status: str = Field(..., description="Status: PENDING, CONFIRMED, REJECTED, AMENDED")
    volume_mw: Optional[float] = Field(None, description="Nominated volume in MW")
    settlement_period: Optional[str] = Field(None, description="Settlement period (HE01-HE24)")
    event_time: Optional[str] = Field(None, description="Business timestamp (ISO 8601)")
    ingest_time: Optional[str] = Field(None, description="Ingest timestamp (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "nomination_id": "NOM-001",
                "deal_id": "DEAL-001",
                "status": "CONFIRMED",
                "volume_mw": 100.0,
                "settlement_period": "HE01",
                "event_time": "2026-08-10T23:12:45.404530",
                "ingest_time": "2026-08-10T23:12:45.404545"
            }
        }


# JSON Schema representations for Kafka topic validation
SCHEMAS = {
    "market.lmp.raw": LmpTick.model_json_schema(),
    "deal.events": DealEvent.model_json_schema(),
    "nomination.events": NominationEvent.model_json_schema(),
}


def get_schema(topic: str) -> dict:
    """Get JSON schema for a topic"""
    return SCHEMAS.get(topic, {})


def validate_event(topic: str, payload: dict) -> bool:
    """Validate event payload against topic schema"""
    schema_class = {
        "market.lmp.raw": LmpTick,
        "deal.events": DealEvent,
        "nomination.events": NominationEvent,
    }.get(topic)

    if not schema_class:
        return False

    try:
        schema_class(**payload)
        return True
    except Exception:
        return False


def print_schemas():
    """Print all schemas in JSON format"""
    for topic, schema in SCHEMAS.items():
        print(f"\n{'='*60}")
        print(f"Topic: {topic}")
        print(f"{'='*60}")
        print(json.dumps(schema, indent=2))
