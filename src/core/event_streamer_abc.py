from abc import ABC, abstractmethod
import time

from eth_defi.provider.multi_provider import MultiProviderWeb3
from eth_defi.event_reader.reorganisation_monitor import ReorganisationMonitor
from eth_defi.event_reader.reorganisation_monitor import ChainReorganisationDetected

from src.utils.logger import get_logger

logger = get_logger(__name__)

class EventStreamer(ABC):
    """ABC event streamer class

    Args:
        ABC (_type_): _description_
    """
    
    def __init__(self, web3: MultiProviderWeb3, reorg_monitor: ReorganisationMonitor, sleep: int = 1):
        """Initialize the event streamer

        Args:
            web3 (Web3): Web3 instance
            reorg_monitor (_type_): Reorg monitor instance
            sleep (int, optional): Sleep time in seconds. Defaults to 1.
        """
        self.web3 = web3
        self.reorg_monitor = reorg_monitor
        self.sleep = sleep
        self.total_reorgs = 0
        
    @abstractmethod
    def fetch_events(self, from_block: int, to_block: int):
        """Fetch events from the blockchain

        Args:
            from_block (int): Starting block number
            to_block (int): Ending block number
        """
        pass

    def stream_events(self): 
        """Stream events from the blockchain using template method pattern
        """
        
        while True:
            try:
                # This is like defining the block window that the reorg monitor will use to fetch events
                chain_reorg_resolution = self.reorg_monitor.update_chain()
                start_block, end_block = chain_reorg_resolution.get_read_range()

                if chain_reorg_resolution.reorg_detected:
                    logger.info(f"Chain reorganisation data updated: {chain_reorg_resolution}")
    
                events = self.fetch_events(start_block=start_block, end_block=end_block)

                for event in events:
                    yield event

            except ChainReorganisationDetected as e:
                # reorg_monitor.update_chain() will detect the fork and purge bad state automatically
                self.total_reorgs += 1
                logger.warning("Chain reorg event raised: %s, we have now detected %d chain reorganisations.", e, self.total_reorgs)
                
            except Exception as e:
                logger.error(f"Unexpected error during event streaming: {e}")

            time.sleep(self.sleep)