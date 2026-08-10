import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from aiokafka import AIOKafkaConsumer
from deltalake import write_deltalake
import pyarrow as pa

# Configuration
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092").split(",")
CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "bronze-ingest")
BRONZE_LOG_LEVEL = os.getenv("BRONZE_LOG_LEVEL", "INFO")

# SMB shared drive path (mounted on Mac)
DELTA_PATH = os.getenv("DELTA_PATH", "/Volumes/personal_folder/data")

TOPIC_LMP = os.getenv("KAFKA_TOPIC_LMP", "market.lmp.raw")
TOPIC_DEALS = os.getenv("KAFKA_TOPIC_DEALS", "deal.events")
TOPIC_NOMINATIONS = os.getenv("KAFKA_TOPIC_NOMINATIONS", "nomination.events")

# Logging
logging.basicConfig(
    level=BRONZE_LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
Path(DELTA_PATH).mkdir(parents=True, exist_ok=True)

# Topics to consume
TOPICS = [TOPIC_LMP, TOPIC_DEALS, TOPIC_NOMINATIONS]


async def consume_and_write():
    """
    Main consumer loop:
    1. Subscribe to Kafka topics
    2. Read messages
    3. Batch write to Delta tables (one per topic)
    """
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BROKERS,
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else None,
    )

    logger.info(f"Starting Bronze consumer for topics: {TOPICS}")
    logger.info(f"Kafka brokers: {KAFKA_BROKERS}")
    logger.info(f"Delta path: {DELTA_PATH}")

    await consumer.start()
    batch_buffer = {topic: [] for topic in TOPICS}
    batch_size = 5  # Write after collecting this many messages (lower for testing)

    try:
        async for message in consumer:
            topic = message.topic
            offset = message.offset
            partition = message.partition
            value = message.value

            # Add metadata
            value["_kafka_offset"] = offset
            value["_kafka_partition"] = partition
            value["_ingest_ts"] = datetime.utcnow().isoformat()

            batch_buffer[topic].append(value)

            # Write batch to Delta when threshold reached
            for batch_topic in TOPICS:
                if len(batch_buffer[batch_topic]) >= batch_size:
                    await write_batch_to_delta(batch_topic, batch_buffer[batch_topic])
                    batch_buffer[batch_topic] = []

    except Exception as e:
        logger.error(f"Consumer error: {e}", exc_info=True)
    finally:
        # Write remaining messages
        for topic in TOPICS:
            if batch_buffer[topic]:
                await write_batch_to_delta(topic, batch_buffer[topic])
        await consumer.stop()
        logger.info("Bronze consumer stopped")


async def write_batch_to_delta(topic: str, messages: list):
    """
    Write a batch of messages to Delta table on SMB shared drive.
    Partitions by asset (delivery_node for LMP, deal_id for deals, etc).

    Structure:
    /data/market_lmp_raw/
      ├── delivery_node=HB_NORTH/
      ├── delivery_node=HB_SOUTH/
      └── delivery_node=HB_HOUSTON/
    """
    if not messages:
        return

    # Clean topic name
    topic_name = topic.replace(".", "_").replace("-", "_")

    # Group messages by asset (partition key depends on topic)
    asset_messages = {}

    for msg in messages:
        # Determine partition key based on topic
        if topic == "market.lmp.raw":
            asset_key = msg.get("delivery_node", "unknown")
        elif topic == "deal.events":
            asset_key = msg.get("deal_id", "unknown")
        elif topic == "nomination.events":
            asset_key = msg.get("nomination_id", "unknown")
        else:
            asset_key = "default"

        if asset_key not in asset_messages:
            asset_messages[asset_key] = []
        asset_messages[asset_key].append(msg)

    # Write each asset's data to its partition directory
    for asset_key, asset_batch in asset_messages.items():
        try:
            # Path: /data/{topic}/asset_key={value}/
            table_path = os.path.join(DELTA_PATH, topic_name, f"asset_key={asset_key}")
            os.makedirs(table_path, exist_ok=True)

            # Convert to PyArrow table
            data = {
                "_raw_payload": [json.dumps(msg) for msg in asset_batch],
                "_kafka_offset": [msg.get("_kafka_offset") for msg in asset_batch],
                "_kafka_partition": [msg.get("_kafka_partition") for msg in asset_batch],
                "_ingest_ts": [msg.get("_ingest_ts") for msg in asset_batch],
            }

            table = pa.table(data)

            # Write to Delta (append mode)
            write_deltalake(table_path, table, mode="append")

            logger.info(
                f"✓ Wrote {len(asset_batch)} messages to {topic_name}/asset_key={asset_key} "
                f"→ {table_path}"
            )
        except Exception as e:
            logger.error(f"Failed to write batch for {asset_key}: {e}", exc_info=True)


async def main():
    """Run the consumer"""
    await consume_and_write()


if __name__ == "__main__":
    asyncio.run(main())
