import os
import argparse
from dotenv import load_dotenv
from prometheus_client import start_http_server
from confluent_kafka import Producer, Consumer
from typing import List

from eth_defi.provider.multi_provider import create_multi_provider_web3
from eth_defi.chain import (
    install_chain_middleware,
    install_retry_middleware,
    install_api_call_counter_middleware,
)
from eth_defi.event_reader.reorganisation_monitor import JSONRPCReorganisationMonitor
from eth_defi.event_reader.block_time import measure_block_time
from eth_defi.provider.multi_provider import MultiProviderWeb3
from prometheus_client import Counter
from src import UniswapV3EventStreamer, KafkaEventConsumer
from src.utils.logger import get_logger

logger = get_logger(__name__)

def setup_web3() -> tuple[MultiProviderWeb3, Counter]:
    """Initialize Web3 with middleware."""
    rpc_url = os.getenv("JSON_RPC_URL")
    if not rpc_url:
        raise ValueError("Missing JSON_RPC_URL")

    web3 = create_multi_provider_web3(rpc_url)
    install_chain_middleware(web3)
    install_retry_middleware(web3)
    api_request_counter = install_api_call_counter_middleware(web3)

    return web3, api_request_counter


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
        event_consumer = KafkaEventConsumer(
            kafka_consumer=consumer,
            kafka_topic=f"uniswap-v3-events",
        )
        return None, event_consumer


def get_checkpoint_path() -> str:
    """Return checkpoint file path (inside/outside Docker)."""
    base_path = "/app/checkpoints" if os.path.exists("/app/checkpoints") else "checkpoints"
    return os.path.join(base_path, f"uni-v3-event-streamer-block-state.csv")


def run_mode(mode: str, event: str):
    """Run in producer or consumer mode."""
    logger.info(f"Running UniswapV3EventStreamer in {mode.upper()} mode for events: {event}...")

    try:
        load_dotenv()
        producer, consumer = setup_kafka(mode)

        if mode == "producer":
            start_http_server(8000)
            web3, api_request_counter = setup_web3()
            pool = os.getenv("POOL_ADDR")
            if not pool:
                raise ValueError("Missing POOL_ADDR")

            reorg_monitor = JSONRPCReorganisationMonitor(web3, check_depth=6)
            block_time = measure_block_time(web3)
            
            kafka_topic = f"uniswap-v3-events"

            streamer = UniswapV3EventStreamer(
                web3=web3,
                event_type=event,
                reorg_monitor=reorg_monitor,
                pool_address=[pool],
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
