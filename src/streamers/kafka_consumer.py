import json
from confluent_kafka import Consumer
from typing import Optional, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)

class KafkaEventConsumer:
    """Dedicated Kafka consumer for Uniswap events
    
    This class handles only the consumption of events from Kafka topics,
    without the overhead of blockchain event streaming infrastructure.
    """
    
    def __init__(self, 
                 kafka_consumer: Consumer,
                 kafka_topic: str,
                 message_handler: Optional[Callable] = None):
        """Initialize the Kafka consumer
        
        Args:
            kafka_consumer (Consumer): Kafka consumer instance
            kafka_topic (str): Kafka topic to consume from
            message_handler (Optional[Callable]): Custom message handler function
        """
        self.kafka_consumer = kafka_consumer
        self.kafka_topic = kafka_topic
        self.message_handler = message_handler or self._default_message_handler
        
        logger.info(f"KafkaEventConsumer initialized for topic: {self.kafka_topic}")
    
    def _default_message_handler(self, event_data: dict):
        """Default message handler that logs the consumed events
        
        Args:
            event_data (dict): Parsed event data from Kafka message
        """
        logger.info(f"Consumed event from topic {self.kafka_topic}:")
        logger.info(f"  Raw event: {event_data.get('raw_event', {})}")
        logger.info(f"  Decoded event: {event_data.get('decoded_event', {})}")
    
    def start_consuming(self):
        """Start consuming events from the Kafka topic"""
        if self.kafka_consumer is None:
            raise ValueError("Kafka consumer is not set")
        
        # Subscribe to the topic
        self.kafka_consumer.subscribe([self.kafka_topic])
        
        logger.info(f"Starting to consume events from topic: {self.kafka_topic}")
        
        try:
            while True:
                # Poll for messages
                msg = self.kafka_consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    # Parse the message
                    event_data = json.loads(msg.value().decode('utf-8'))
                    
                    # Process the message using the handler
                    self.message_handler(event_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted, shutting down...")
        finally:
            # Close the consumer
            self.kafka_consumer.close()
            logger.info("Consumer closed") 