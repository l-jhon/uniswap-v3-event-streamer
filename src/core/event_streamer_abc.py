from abc import ABC, abstractmethod
import time
from pathlib import Path
from typing import Optional
from tqdm import tqdm

from eth_defi.provider.multi_provider import MultiProviderWeb3
from eth_defi.event_reader.reorganisation_monitor import ReorganisationMonitor
from eth_defi.event_reader.reorganisation_monitor import ChainReorganisationDetected
from eth_defi.event_reader.csv_block_data_store import CSVDatasetBlockDataStore
from eth_defi.event_reader.reader import read_events, LogResult
from eth_defi.event_reader.filter import Filter

from src.utils.logger import get_logger

logger = get_logger(__name__)

class EventStreamer(ABC):
    """ABC event streamer class

    Args:
        ABC (_type_): _description_
    """
    
    def __init__(self, 
                 web3: MultiProviderWeb3, 
                 reorg_monitor: ReorganisationMonitor, 
                 sleep: float,
                 event_filter: Filter,
                 block_state_path: Optional[str] = None,
                 initial_block_count: int = 10,
                 stats_save_interval: float = 10.0):
        """Initialize the event streamer

        Args:
            web3 (Web3): Web3 instance
            reorg_monitor (_type_): Reorg monitor instance
            sleep (float): Sleep time in seconds
            event_filter (Filter): Event filter to use for fetching events
            block_state_path (Optional[str]): Path to save block state checkpoint. If None, no checkpointing is done.
            initial_block_count (int): Number of initial blocks to load if starting fresh
            stats_save_interval (float): How often to save stats and block state (in seconds)
        """
        self.web3 = web3
        self.reorg_monitor = reorg_monitor
        self.sleep = sleep
        self.total_reorgs = 0
        self.stats_save_interval = stats_save_interval
        self.next_stats_save = time.time() + stats_save_interval
        self.event_filter = event_filter
        
        if block_state_path:
            self.block_store = CSVDatasetBlockDataStore(Path(block_state_path))
            self._initialize_block_state(initial_block_count)
        else:
            self.block_store = None
            logger.info(f"Block state checkpointing disabled. Initializing reorg monitor with {initial_block_count} current blocks.")
            self.reorg_monitor.load_initial_block_headers(initial_block_count, tqdm=tqdm)
        
    def _initialize_block_state(self, initial_block_count: int):
        """Initialize block state from checkpoint or fresh start"""
        if not self.block_store.is_virgin():
            block_header_df = self.block_store.load()
            self.reorg_monitor.load_pandas(block_header_df)
            logger.info(f"Loaded {len(block_header_df)} existing blocks from {self.block_store.path}.\nIf the save checkpoint was long time ago, we need to catch up all blocks and it could be slow.")
        else:
            logger.info(f"Starting with fresh block header store at {self.block_store.path}, cold start fetching {initial_block_count} blocks")
            self.reorg_monitor.load_initial_block_headers(initial_block_count, tqdm=tqdm)
        
    def _save_block_state(self):
        """Save current block state to checkpoint file"""
        if self.block_store:
            try:
                df = self.reorg_monitor.to_pandas()
                self.block_store.save(df)
                logger.debug(f"Block state saved to {self.block_store.path}")
            except Exception as e:
                logger.error(f"Failed to save block state: {e}")
        
    def fetch_events(self, start_block: int, end_block: int):
        """Fetch events from the blockchain using the configured filter

        Args:
            start_block (int): Starting block number
            end_block (int): Ending block number
        """
        logger.info(f"Fetching events from block {start_block} to {end_block}")

        events = read_events(
            web3=self.web3, 
            filter=self.event_filter, 
            start_block=start_block, 
            end_block=end_block,
            extract_timestamps=None,
            reorg_mon=self.reorg_monitor
        )
        
        return events

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

                if time.time() > self.next_stats_save:
                    self._save_block_state()
                    logger.info("**STATS** Reorgs detected: %d, block headers buffered: %d", 
                               self.total_reorgs, len(self.reorg_monitor.block_map))
                    self.next_stats_save = time.time() + self.stats_save_interval

            except ChainReorganisationDetected as e:
                # reorg_monitor.update_chain() will detect the fork and purge bad state automatically
                self.total_reorgs += 1
                logger.warning("Chain reorg event raised: %s, we have now detected %d chain reorganisations.", e, self.total_reorgs)
                
            except Exception as e:
                logger.error(f"Unexpected error during event streaming: {e}")

            time.sleep(self.sleep)

    @abstractmethod
    def decode_event(self, event: LogResult) -> dict:
        """Decode the event into a dictionary

        Args:
            event (LogResult): The event to decode
        """
        pass

    @abstractmethod
    def event_producer(self):
        """Produce events to the Kafka topic
        """
        pass

    @abstractmethod
    def event_consumer(self):
        """Consume events from the Kafka topic
        """