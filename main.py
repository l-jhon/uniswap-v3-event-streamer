import os
import argparse
from dotenv import load_dotenv
from prometheus_client import start_http_server
from confluent_kafka import Producer, Consumer

from eth_defi.provider.multi_provider import create_multi_provider_web3
from eth_defi.chain import (
    install_chain_middleware,
    install_retry_middleware,
    install_api_call_counter_middleware,
)
from eth_defi.event_reader.reorganisation_monitor import JSONRPCReorganisationMonitor
from eth_defi.event_reader.block_time import measure_block_time

from src import UniswapSwapStreamer


def setup_web3():
    """Initialize Web3 with middleware."""
    rpc_url = os.getenv("JSON_RPC_URL")
    if not rpc_url:
        raise ValueError("Missing JSON_RPC_URL")

    web3 = create_multi_provider_web3(rpc_url)
    install_chain_middleware(web3)
    install_retry_middleware(web3)
    install_api_call_counter_middleware(web3)

    return web3


def setup_kafka(mode: str, event: str):
    """Initialize Kafka producer or consumer based on mode."""
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVER")
    if not bootstrap:
        raise ValueError("Missing KAFKA_BOOTSTRAP_SERVER")

    if mode == "producer":
        return Producer({"bootstrap.servers": bootstrap}), None
    else:
        consumer = Consumer({
            "bootstrap.servers": bootstrap,
            "group.id": f"uniswap-v3-{event}-consumer",
            "auto.offset.reset": "earliest",
        })
        return None, consumer


def get_checkpoint_path(event: str) -> str:
    """Return checkpoint file path (inside/outside Docker)."""
    base_path = "/app/checkpoints" if os.path.exists("/app/checkpoints") else "checkpoints"
    return os.path.join(base_path, f"uni-v3-{event}-streamer-block-state.csv")


def run_mode(mode: str, event: str):
    """Run in producer or consumer mode."""
    print(f"Running UniswapSwapStreamer in {mode.upper()} mode...")

    load_dotenv()
    start_http_server(8000)

    web3 = setup_web3()
    producer, consumer = setup_kafka(mode, event)
    pool = os.getenv("POOL_ADDR")
    if not pool:
        raise ValueError("Missing POOL_ADDR")

    reorg_monitor = JSONRPCReorganisationMonitor(web3, check_depth=6)
    block_time = measure_block_time(web3)

    streamer = UniswapSwapStreamer(
        web3=web3,
        reorg_monitor=reorg_monitor,
        pool_address=pool,
        sleep=block_time,
        kafka_topic=f"uniswap-v3-{event}",
        kafka_producer=producer,
        kafka_consumer=consumer,
        block_state_path=get_checkpoint_path(),
        initial_block_count=10,
        stats_save_interval=10.0
    )

    if mode == "producer":
        streamer.event_producer()
    else:
        streamer.event_consumer()


def main():
    parser = argparse.ArgumentParser(description="Uniswap V3 Event Streamer")
    parser.add_argument("--mode", choices=["producer", "consumer"], help="Mode to run")
    parser.add_argument("--event", choices=["swap", "mint", "burn"], help="Event name to stream")
    args = parser.parse_args()

    try:
        run_mode(args.mode)
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
