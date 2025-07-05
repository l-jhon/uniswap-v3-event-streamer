from abc import ABC, abstractmethod
import time
import logging

from web3 import Web3
from eth_defi.event_reader.reorganisation_monitor import ReorganisationMonitor

logger = logging.getLogger(__name__)

class EventStreamer(ABC):
    """ABC event streamer class

    Args:
        ABC (_type_): _description_
    """
    
    def __init__(self, web3: Web3, reorg_monitor: ReorganisationMonitor, sleep: int = 1):
        """Initialize the event streamer

        Args:
            web3 (Web3): Web3 instance
            reorg_monitor (_type_): Reorg monitor instance
            sleep (int, optional): Sleep time in seconds. Defaults to 1.
        """
        self.web3 = web3
        self.reorg_monitor = reorg_monitor
        self.sleep = sleep
        
    @abstractmethod
    def fetch_events(self, from_block: int, to_block: int):
        """Fetch events from the blockchain

        Args:
            from_block (int): Starting block number
            to_block (int): Ending block number
        """
        pass

    @abstractmethod
    def parse_event(self, event: dict) -> dict:
        """Parse the event

        Args:
            event (dict): Event dictionary
        """
        pass

    def stream_events(self): 
        """Stream events from the blockchain
        """
        
        while True:
            # Resolution can be understood as the block window that the reorg monitor will use to fetch events
            chain_reorg_resolution = self.reorg_monitor.update_chain()
            start_block, end_block = chain_reorg_resolution.get_block_range()

            if chain_reorg_resolution.reorg_detected:
                logger.warning("Reorg detected, skipping block range")
    
            events = self.fetch_events(start_block, end_block)

            for event in events:
                self.parse_event(event)

            time.sleep(self.sleep)