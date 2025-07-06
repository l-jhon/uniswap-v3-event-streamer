import json
from confluent_kafka import Consumer
from src.utils.logger import get_logger
from src.utils.postgresql_client import PostgresClient
from src.models.swap_events import SwapEvent
from src.models.burn_events import BurnEvent
from src.models.mint_events import MintEvent

logger = get_logger(__name__)

class KafkaEventConsumer:
    """Dedicated Kafka consumer for Uniswap events
    
    This class handles only the consumption of events from Kafka topics,
    without the overhead of blockchain event streaming infrastructure.
    """
    
    def __init__(self, 
                 kafka_consumer: Consumer,
                 kafka_topic: str):
        """Initialize the Kafka consumer
        
        Args:
            kafka_consumer (Consumer): Kafka consumer instance
            kafka_topic (str): Kafka topic to consume from
        """
        self.kafka_consumer = kafka_consumer
        self.kafka_topic = kafka_topic
        self.postgres_client = PostgresClient()
        
        logger.info(f"KafkaEventConsumer initialized for topic: {self.kafka_topic}")
    
    def _handle_message(self, event_data: dict):
        """Handle incoming event message by routing to appropriate event model
        
        Args:
            event_data (dict): Parsed event data from Kafka message
        """
        if event_data['event_name'] == 'Swap':
            swap_event = SwapEvent(**event_data)
            self.postgres_client.insert_event(swap_event)
        elif event_data['event_name'] == 'Burn':
            burn_event = BurnEvent(**event_data)
            self.postgres_client.insert_event(burn_event)
        elif event_data['event_name'] == 'Mint':
            mint_event = MintEvent(**event_data)
            self.postgres_client.insert_event(mint_event)
    
    def start_consuming(self):
        """Start consuming events from the Kafka topic"""
        if self.kafka_consumer is None:
            raise ValueError("Kafka consumer is not set")
        
        self.kafka_consumer.subscribe([self.kafka_topic])
        
        logger.info(f"Starting to consume events from topic: {self.kafka_topic}")
        
        try:
            while True:
                msg = self.kafka_consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    event_data = json.loads(msg.value().decode('utf-8'))
                    decoded_event = event_data.get('decoded_event')
                    if decoded_event:
                        self._handle_message(decoded_event)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted, shutting down...")
        finally:
            self.kafka_consumer.close()
            self.postgres_client.close()
            logger.info("Consumer closed") 