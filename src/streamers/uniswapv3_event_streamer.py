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
from typing import List, Optional
from src.utils.logger import get_logger
from eth_defi.uniswap_v3.events import decode_swap, decode_mint, decode_burn
from src.utils.datetime_encoder import DateTimeEncoder
from prometheus_client import Counter

logger = get_logger(__name__)
class UniswapV3EventStreamer(EventStreamer):
    """Uniswap swap events streamer

    Args:
        EventStreamer (_type_): _description_
    """
    
    def __init__(self, 
                 web3: MultiProviderWeb3,
                 event_type: str,
                 reorg_monitor: ReorganisationMonitor, 
                 pool_address: Optional[str | List[str]], 
                 sleep: float,
                 kafka_topic: str,
                 kafka_producer: Optional[Producer] = None,
                 block_state_path: Optional[str] = None,
                 initial_block_count: int = 10,
                 stats_save_interval: float = 10.0,
                 api_request_counter: Optional[Counter] = None):
        """Initialize the UniswapV3EventStreamer

        Args:
            web3 (MultiProviderWeb3): Web3 instance
            event_type (str): Event type to filter (swap, mint, burn, all)
            reorg_monitor (ReorganisationMonitor): Reorganisation monitor instance
            pool_address (Optional[str | List[str]]): Pool address to filter (can be a list of addresses)
            sleep (float): Sleep time in seconds
            kafka_topic (str): Kafka topic to produce events to
            kafka_producer (Optional[Producer]): Kafka producer instance
            block_state_path (Optional[str]): Path to save block state checkpoint
            initial_block_count (int): Number of initial blocks to load if starting fresh
            stats_save_interval (float): How often to save stats and block state (in seconds)
            api_request_counter (Counter): Counter for API requests
        """
        
        self.uniswap_v3_deployment = fetch_deployment(
            web3,
            factory_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["factory"],
            router_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["router"],
            position_manager_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["position_manager"],
            quoter_address=UNISWAP_V3_DEPLOYMENTS["ethereum"]["quoter"],
        )
        self.swap_event_abi = self.uniswap_v3_deployment.PoolContract.events.Swap
        self.mint_event_abi = self.uniswap_v3_deployment.PoolContract.events.Mint
        self.burn_event_abi = self.uniswap_v3_deployment.PoolContract.events.Burn
        self.pool_address = pool_address

        self.event_abi_map = {
            "swap": [self.swap_event_abi],
            "mint": [self.mint_event_abi],
            "burn": [self.burn_event_abi],
            "all": [self.swap_event_abi, self.mint_event_abi, self.burn_event_abi]
        }

        self.event_filter = Filter.create_filter(
            address=self.pool_address, 
            event_types=self.event_abi_map[event_type]
        )

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
    
        logger.info(f"UniswapV3EventStreamer initialized for pool: {self.pool_address}")


    def decode_event(self, event: LogResult) -> dict:
        """Decode the event into a dictionary

        Args:
            event (LogResult): The event to decode
        """
        try:
            if event['event'].event_name == "Swap":
                decoded_event = decode_swap(event)
            elif event['event'].event_name == "Mint":
                decoded_event = decode_mint(event)
            elif event['event'].event_name == "Burn":
                decoded_event = decode_burn(event)
            else:
                raise ValueError(f"Invalid event type: {event['event'].event_name}")

            pool_details = fetch_pool_details(self.web3, event['address'])
            decoded_event['event_name'] = event['event'].event_name
            decoded_event["pool_details"] = str(pool_details)
            decoded_event["pool_fee"] = pool_details.fee
            decoded_event["token0_address"] = pool_details.token0.address
            decoded_event["token1_address"] = pool_details.token1.address
            decoded_event["token0_symbol"] = pool_details.token0.symbol
            decoded_event["token1_symbol"] = pool_details.token1.symbol
            decoded_event["token0_decimals"] = pool_details.token0.decimals
            decoded_event["token1_decimals"] = pool_details.token1.decimals
            decoded_event["token0_name"] = pool_details.token0.name
            decoded_event["token1_name"] = pool_details.token1.name
            decoded_event["token0_total_supply"] = pool_details.token0.total_supply 
            decoded_event["token1_total_supply"] = pool_details.token1.total_supply
            decoded_event["record_timestamp"] = datetime.datetime.now(datetime.timezone.utc)

            return decoded_event
        
        except Exception as e:
            logger.error(f"Error decoding event: {e}")
            raise

    def event_producer(self):
        """Produce events to the Kafka topic
        """
        if self.kafka_producer is None:
            raise ValueError("Kafka producer is not set")
        
        for raw_event in self.stream_events():
            logger.info(f"Event received: {raw_event['event'].event_name}")
            decoded_event = self.decode_event(raw_event)
            raw_event['event_name'] = raw_event['event'].event_name
            raw_event['record_timestamp'] = datetime.datetime.now(datetime.timezone.utc)
            del raw_event['event']
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

