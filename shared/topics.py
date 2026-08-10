"""Kafka topic configuration"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TopicConfig:
    """Topic configuration"""
    name: str
    partitions: int = 3
    replication_factor: int = 1
    retention_ms: int = 86400000  # 24 hours default
    description: str = ""


# Topic catalog
TOPICS = {
    "market.lmp.raw": TopicConfig(
        name="market.lmp.raw",
        partitions=3,
        replication_factor=1,
        retention_ms=86400000,
        description="Market LMP (Locational Marginal Price) ticks from ERCOT"
    ),
    "deal.events": TopicConfig(
        name="deal.events",
        partitions=3,
        replication_factor=1,
        retention_ms=604800000,  # 7 days
        description="Power trading deal events (NEW, AMENDED, CANCELLED)"
    ),
    "nomination.events": TopicConfig(
        name="nomination.events",
        partitions=3,
        replication_factor=1,
        retention_ms=604800000,  # 7 days
        description="Energy scheduling nominations and amendments"
    ),
}


def get_topic_config(topic_name: str) -> TopicConfig:
    """Get configuration for a topic"""
    return TOPICS.get(topic_name)


def list_topics() -> List[str]:
    """List all topic names"""
    return list(TOPICS.keys())


def print_topic_info():
    """Print all topic information"""
    for topic_name, config in TOPICS.items():
        print(f"\n{'='*60}")
        print(f"Topic: {topic_name}")
        print(f"{'='*60}")
        print(f"  Partitions: {config.partitions}")
        print(f"  Replication: {config.replication_factor}")
        print(f"  Retention: {config.retention_ms / 1000 / 3600 / 24:.1f} days")
        print(f"  Description: {config.description}")
