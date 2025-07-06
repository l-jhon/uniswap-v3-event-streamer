import json
import datetime
from src import EventStreamer
from eth_defi.event_reader.reorganisation_monitor import ReorganisationMonitor
from eth_defi.provider.multi_provider import MultiProviderWeb3
from eth_defi.event_reader.filter import Filter
from eth_defi.uniswap_v3.deployment import fetch_deployment
from eth_defi.uniswap_v3.pool import fetch_pool_details
from eth_defi.uniswap_v3.constants import UNISWAP_V3_DEPLOYMENTS
from eth_defi.event_reader.logresult import LogResult
from confluent_kafka import Producer, Consumer
from typing import Optional
from src.utils.logger import get_logger
from eth_defi.uniswap_v3.events import decode_swap
from src.utils.datetime_encoder import DateTimeEncoder
from prometheus_client import Counter

logger = get_logger(__name__)
class UniswapSwapStreamer(EventStreamer):
    """Uniswap swap events streamer

    Args:
        EventStreamer (_type_): _description_
    """
    
    def __init__(self, 
                 web3: MultiProviderWeb3, 
                 reorg_monitor: ReorganisationMonitor, 
                 pool_address: str, 
                 sleep: float,
                 kafka_topic: str,
                 kafka_producer: Optional[Producer] = None,
                 kafka_consumer: Optional[Consumer] = None,
                 block_state_path: Optional[str] = None,
                 initial_block_count: int = 10,
                 stats_save_interval: float = 10.0,
                 api_request_counter: Optional[Counter] = None):
        
        self.pool_address = pool_address
        self.pool_details = fetch_pool_details(web3, self.pool_address)
        self.pool_deployment = fetch_deployment(
            web3,
            factory_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["factory"],
            router_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["router"],
            position_manager_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["position_manager"],
            quoter_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["quoter"],
        )
        self.event_abi = self.pool_deployment.PoolContract.events.Swap
        self.event_filter = Filter.create_filter(address=self.pool_address, event_types=[self.event_abi])

        super().__init__(
            web3=web3, 
            reorg_monitor=reorg_monitor, 
            sleep=sleep, 
            event_filter=self.event_filter,
            block_state_path=block_state_path, 
            initial_block_count=initial_block_count, 
            stats_save_interval=stats_save_interval,
            api_request_counter=api_request_counter
        )
        self.kafka_topic = kafka_topic
        self.kafka_producer = kafka_producer
        self.kafka_consumer = kafka_consumer
    
        logger.info(f"UniswapSwapStreamer initialized for pool: {pool_address}")

    def decode_event(self, event: LogResult) -> dict:
        """Decode the event into a dictionary

        Args:
            event (LogResult): The event to decode
        """

        decoded_event = decode_swap(event)
        decoded_event["pool_details"] = str(self.pool_details)
        decoded_event["pool_fee"] = self.pool_details.fee
        decoded_event["token0_address"] = self.pool_details.token0.address
        decoded_event["token1_address"] = self.pool_details.token1.address
        decoded_event["token0_symbol"] = self.pool_details.token0.symbol
        decoded_event["token1_symbol"] = self.pool_details.token1.symbol
        decoded_event["token0_decimals"] = self.pool_details.token0.decimals
        decoded_event["token1_decimals"] = self.pool_details.token1.decimals
        decoded_event["token0_name"] = self.pool_details.token0.name
        decoded_event["token1_name"] = self.pool_details.token1.name
        decoded_event["token0_total_supply"] = self.pool_details.token0.total_supply 
        decoded_event["token1_total_supply"] = self.pool_details.token1.total_supply
        decoded_event["record_timestamp"] = datetime.datetime.now(datetime.timezone.utc)

        return decoded_event

    def event_producer(self):
        """Produce events to the Kafka topic
        """
        if self.kafka_producer is None:
            raise ValueError("Kafka producer is not set")
        
        for raw_event in self.stream_events():
            decoded_event = self.decode_event(raw_event)
            del raw_event['event']
            raw_event['event_name'] = 'Swap'
            raw_event['record_timestamp'] = datetime.datetime.now(datetime.timezone.utc)
            self.kafka_producer.produce(
                topic=self.kafka_topic,
                value=json.dumps(
                    {
                        "raw_event": raw_event,
                        "decoded_event": decoded_event
                    },
                    cls=DateTimeEncoder
                )
            )
            self.kafka_producer.flush()

    def event_consumer(self):
        """Consume events from the Kafka topic
        """
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
                    
                    # Log the consumed event
                    logger.info(f"Consumed event from topic {self.kafka_topic}:")
                    logger.info(f"  Raw event: {event_data.get('raw_event', {})}")
                    logger.info(f"  Decoded event: {event_data.get('decoded_event', {})}")
                    
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