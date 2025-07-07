import os

from eth_defi.provider.multi_provider import create_multi_provider_web3
from eth_defi.chain import (
    install_chain_middleware,
    install_retry_middleware,
    install_api_call_counter_middleware,
)
from eth_defi.provider.multi_provider import MultiProviderWeb3
from prometheus_client import Counter

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