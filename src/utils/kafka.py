import time
import os
from confluent_kafka import Producer, Consumer, KafkaException
from typing import List
from src.utils.logger import get_logger
from src.streamers.kafka_consumer import KafkaEventConsumer

logger = get_logger(__name__)

def wait_for_topic(consumer, topic, timeout=60, retry_interval=5):
    """Wait for a Kafka topic to be available."""
    logger.info(f"Waiting for Kafka topic '{topic}' to be available...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            metadata = consumer.list_topics(timeout=5)
            if topic in metadata.topics:
                logger.info(f"Topic '{topic}' is now available.")
                return
            else:
                logger.warning(f"Topic '{topic}' not found. Retrying in {retry_interval}s...")
        except KafkaException as e:
            logger.error(f"Error checking topic: {e}")
        time.sleep(retry_interval)

    raise TimeoutError(f"Timeout while waiting for Kafka topic '{topic}'")

def setup_kafka(mode: str):
    """Initialize Kafka producer or consumer based on mode."""
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVER")
    if not bootstrap:
        raise ValueError("Missing KAFKA_BOOTSTRAP_SERVER")

    if mode == "producer":
        return Producer({"bootstrap.servers": bootstrap}), None
    else:
        consumer = Consumer({
            "bootstrap.servers": bootstrap,
            "group.id": f"uniswap-v3-events-consumer",
            "auto.offset.reset": "earliest",
        })
        wait_for_topic(consumer, "uniswap-v3-events")
        logger.info(f"Kafka topic 'uniswap-v3-events' is now available.")
        event_consumer = KafkaEventConsumer(
            kafka_consumer=consumer,
            kafka_topic=f"uniswap-v3-events",
        )
        return None, event_consumer