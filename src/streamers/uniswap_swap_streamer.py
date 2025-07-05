from src import EventStreamer
from eth_defi.event_reader.reorganisation_monitor import ReorganisationMonitor
from eth_defi.provider.multi_provider import MultiProviderWeb3
from eth_defi.event_reader.reader import read_events
from eth_defi.event_reader.filter import Filter
from eth_defi.uniswap_v3.deployment import fetch_deployment
from eth_defi.uniswap_v3.pool import fetch_pool_details
from eth_defi.uniswap_v3.constants import UNISWAP_V3_DEPLOYMENTS
from confluent_kafka import Producer
from src.utils.logger import get_logger

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
                 kafka_producer: Producer = None,
                 sleep: int = 1):
        super().__init__(web3, reorg_monitor, sleep)
        
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
        self.filter = Filter.create_filter(address=self.pool_address, event_types=[self.event_abi])
        self.kafka_producer = kafka_producer
        
        logger.info(f"UniswapSwapStreamer initialized for pool: {pool_address}")
        
    def fetch_events(self, start_block: int, end_block: int):
        """Fetch events from the blockchain

        Args:
            from_block (int): Starting block number
            to_block (int): Ending block number
        """

        logger.info(f"Fetching events from block {start_block} to {end_block}")

        events = read_events(
            web3=self.web3, 
            filter=self.filter, 
            start_block=start_block, 
            end_block=end_block,
            extract_timestamps=None,
            reorg_mon=self.reorg_monitor
        )
        
        return events

        

