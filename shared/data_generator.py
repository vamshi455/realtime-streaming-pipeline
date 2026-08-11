"""Synthetic data generator with faker and templates"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from faker import Faker

fake = Faker()


class DataGenerator:
    """Generate synthetic data based on schema templates"""

    def __init__(self):
        self.templates = {
            "lmp_tick": self._generate_lmp_tick,
            "deal_event": self._generate_deal_event,
            "nomination_event": self._generate_nomination_event,
            "iot_sensor": self._generate_iot_sensor,
            "financial_price": self._generate_financial_price,
        }

    def generate(
        self,
        event_type: str,
        count: int = 1,
        **constraints
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic events.

        Args:
            event_type: Type of event (lmp_tick, deal_event, etc.)
            count: Number of events to generate
            **constraints: Field-specific constraints
                - lmp_range: (min, max) tuple
                - nodes: list of delivery nodes
                - deal_types: list of deal types
                - etc.

        Returns:
            List of generated event dictionaries
        """
        if event_type not in self.templates:
            raise ValueError(f"Unknown event type: {event_type}")

        generator_fn = self.templates[event_type]
        return [generator_fn(**constraints) for _ in range(count)]

    def _generate_lmp_tick(self, **kwargs) -> Dict:
        """Generate LMP (Locational Marginal Price) tick"""
        lmp_range = kwargs.get("lmp_range", (35.0, 60.0))
        nodes = kwargs.get("nodes", ["HB_NORTH", "HB_SOUTH", "HB_HOUSTON"])

        return {
            "delivery_node": random.choice(nodes),
            "lmp": round(random.uniform(*lmp_range), 2),
            "event_time": datetime.utcnow().isoformat(),
            "ingest_time": datetime.utcnow().isoformat(),
        }

    def _generate_deal_event(self, **kwargs) -> Dict:
        """Generate power trading deal event"""
        deal_types = kwargs.get("deal_types", ["NEW", "AMENDED", "CANCELLED"])
        volume_range = kwargs.get("volume_range", (50.0, 500.0))

        return {
            "deal_id": f"DEAL-{fake.random_int(10000, 99999)}",
            "event_type": random.choice(deal_types),
            "volume_mw": round(random.uniform(*volume_range), 2),
            "counterparty": fake.company(),
            "event_time": datetime.utcnow().isoformat(),
            "ingest_time": datetime.utcnow().isoformat(),
        }

    def _generate_nomination_event(self, **kwargs) -> Dict:
        """Generate energy scheduling nomination"""
        statuses = kwargs.get("statuses", ["PENDING", "CONFIRMED", "REJECTED", "AMENDED"])
        volume_range = kwargs.get("volume_range", (50.0, 300.0))

        return {
            "nomination_id": f"NOM-{fake.random_int(10000, 99999)}",
            "deal_id": f"DEAL-{fake.random_int(10000, 99999)}",
            "status": random.choice(statuses),
            "volume_mw": round(random.uniform(*volume_range), 2),
            "settlement_period": f"HE{fake.random_int(1, 24):02d}",
            "event_time": datetime.utcnow().isoformat(),
            "ingest_time": datetime.utcnow().isoformat(),
        }

    def _generate_iot_sensor(self, **kwargs) -> Dict:
        """Generate IoT sensor reading"""
        sensor_types = kwargs.get("sensor_types", ["temperature", "humidity", "pressure"])
        sensor_type = random.choice(sensor_types)
        location = kwargs.get("location", fake.city())

        ranges = {
            "temperature": (15.0, 35.0),
            "humidity": (20.0, 90.0),
            "pressure": (980.0, 1020.0),
        }

        return {
            "sensor_id": f"SENSOR-{fake.random_int(1000, 9999)}",
            "sensor_type": sensor_type,
            "location": location,
            "value": round(random.uniform(*ranges[sensor_type]), 2),
            "unit": {"temperature": "C", "humidity": "%", "pressure": "hPa"}[sensor_type],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _generate_financial_price(self, **kwargs) -> Dict:
        """Generate financial price tick"""
        symbol = kwargs.get("symbol", "AAPL")
        price_range = kwargs.get("price_range", (100.0, 200.0))

        return {
            "symbol": symbol,
            "price": round(random.uniform(*price_range), 2),
            "volume": fake.random_int(1000000, 10000000),
            "bid": round(random.uniform(*price_range)[0], 2),
            "ask": round(random.uniform(*price_range)[1], 2),
            "timestamp": datetime.utcnow().isoformat(),
        }


def parse_natural_language_prompt(prompt: str) -> Dict[str, Any]:
    """
    Parse natural language prompt into generation parameters.

    Examples:
    - "Generate 100 LMP ticks for HB_NORTH between 40 and 50"
    - "Create 50 deal events with volumes 100-500"
    - "500 IoT sensor readings for temperature between 20-30"

    Returns:
        Dict with keys: event_type, count, constraints
    """
    prompt_lower = prompt.lower()

    # Detect event type
    event_type = None
    if "lmp" in prompt_lower or "price tick" in prompt_lower:
        event_type = "lmp_tick"
    elif "deal" in prompt_lower:
        event_type = "deal_event"
    elif "nomination" in prompt_lower:
        event_type = "nomination_event"
    elif "iot" in prompt_lower or "sensor" in prompt_lower:
        event_type = "iot_sensor"
    elif "financial" in prompt_lower or "price" in prompt_lower:
        event_type = "financial_price"

    if not event_type:
        raise ValueError(f"Could not parse event type from: {prompt}")

    # Extract count (e.g., "100 LMP")
    import re
    count_match = re.search(r"(\d+)\s+(lmp|deal|nomination|sensor|price|tick|event|reading)", prompt_lower)
    count = int(count_match.group(1)) if count_match else 1

    # Extract ranges (e.g., "between 40 and 50")
    range_match = re.search(r"between\s+([\d.]+)\s+and\s+([\d.]+)", prompt_lower)
    constraints = {}

    if range_match:
        min_val = float(range_match.group(1))
        max_val = float(range_match.group(2))

        if event_type == "lmp_tick":
            constraints["lmp_range"] = (min_val, max_val)
        elif event_type == "iot_sensor":
            constraints["value_range"] = (min_val, max_val)
        elif event_type == "financial_price":
            constraints["price_range"] = (min_val, max_val)
        elif event_type == "deal_event":
            constraints["volume_range"] = (min_val, max_val)

    # Extract node/location (e.g., "for HB_NORTH")
    node_match = re.search(r"(?:for|at)\s+([A-Z_]+)", prompt)
    if node_match:
        if event_type == "lmp_tick":
            constraints["nodes"] = [node_match.group(1)]
        elif event_type == "iot_sensor":
            constraints["location"] = node_match.group(1)

    return {
        "event_type": event_type,
        "count": count,
        "constraints": constraints,
    }


if __name__ == "__main__":
    # Test
    gen = DataGenerator()

    print("=== LMP Ticks ===")
    lmp_events = gen.generate("lmp_tick", count=3, lmp_range=(40, 50))
    for event in lmp_events:
        print(json.dumps(event, indent=2))

    print("\n=== Deal Events ===")
    deal_events = gen.generate("deal_event", count=2)
    for event in deal_events:
        print(json.dumps(event, indent=2))

    print("\n=== Parse NLP ===")
    prompt = "Generate 100 LMP ticks for HB_NORTH between 40 and 50"
    params = parse_natural_language_prompt(prompt)
    print(json.dumps(params, indent=2))
