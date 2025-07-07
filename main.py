import os
import argparse
from dotenv import load_dotenv
from prometheus_client import start_http_server

from eth_defi.event_reader.reorganisation_monitor import JSONRPCReorganisationMonitor
from eth_defi.event_reader.block_time import measure_block_time
from src import UniswapV3EventStreamer
from src.utils.logger import get_logger
from src.utils.web3 import setup_web3
from src.utils.filesystem import get_checkpoint_path
from src.utils.kafka import setup_kafka

logger = get_logger(__name__)

def get_pool_addresses():
    """Get pool addresses from environment variables.
    
    Returns:
        list: List of pool addresses. Supports both single pool and comma-separated
              multiple pools using POOL_ADDRESSES variable.
    """
    pool_addresses = os.getenv("POOL_ADDRESSES")
    if not pool_addresses:
        raise ValueError("Missing POOL_ADDRESSES environment variable")
    
    # Split by comma and strip whitespace
    addresses = [addr.strip() for addr in pool_addresses.split(",") if addr.strip()]
    
    if not addresses:
        raise ValueError("POOL_ADDRESSES is empty or contains no valid addresses")
    
    logger.info(f"Found {len(addresses)} pool address(es): {addresses}")
    return addresses

def run_mode(mode: str, event: str):
    """Run in producer or consumer mode."""
    logger.info(f"Running UniswapV3EventStreamer in {mode.upper()} mode for events: {event}...")

    try:
        load_dotenv()
        producer, consumer = setup_kafka(mode)

        if mode == "producer":
            start_http_server(8000)
            web3, api_request_counter = setup_web3()
            pool_addresses = get_pool_addresses()

            reorg_monitor = JSONRPCReorganisationMonitor(web3, check_depth=6)
            block_time = measure_block_time(web3)
            
            kafka_topic = f"uniswap-v3-events"

            streamer = UniswapV3EventStreamer(
                web3=web3,
                event_type=event,
                reorg_monitor=reorg_monitor,
                pool_address=pool_addresses,
                sleep=block_time,
                kafka_topic=kafka_topic,
                kafka_producer=producer,
                block_state_path=get_checkpoint_path(),
                initial_block_count=10,
                stats_save_interval=10.0,
                api_request_counter=api_request_counter
            )

            streamer.event_producer()
        else:
            start_http_server(8001)
            consumer.start_consuming()
            
    except Exception as e:
        logger.error(f"Error in run_mode: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Uniswap V3 Event Streamer")
    parser.add_argument("--mode", choices=["producer", "consumer"], required=True, help="Mode to run")
    parser.add_argument("--event", choices=["swap", "mint", "burn", "all"], 
                       help="Event(s) to stream (only required for producer mode). Can be: 'swap', 'mint', 'burn', or 'all'")
    args = parser.parse_args()

    if args.mode == "producer" and not args.event:
        parser.error("--event is required when running in producer mode")

    event = args.event if args.event else "all"

    try:
        run_mode(args.mode, event)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
