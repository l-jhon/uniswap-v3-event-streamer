#!/usr/bin/env python3
"""
Simple pytest tests for EventStreamer Prometheus metrics.
"""

import pytest
from unittest.mock import Mock
from prometheus_client import REGISTRY, generate_latest

from src.core.event_streamer_abc import EventStreamer  # Replace with actual import


class MockEventStreamer(EventStreamer):
    """Concrete implementation for testing"""
    
    def decode_event(self, event):
        return {"test": "event"}
    
    def event_producer(self):
        pass


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for EventStreamer"""
    web3 = Mock()
    web3.eth.chain_id = 1  # Ethereum mainnet
    
    reorg_monitor = Mock()
    reorg_monitor.block_map = {}  # Empty initially
    
    event_filter = Mock()
    
    api_counter = Mock()
    api_counter._value.get.return_value = 100
    
    return {
        'web3': web3,
        'reorg_monitor': reorg_monitor,
        'event_filter': event_filter,
        'api_counter': api_counter
    }


@pytest.fixture
def event_streamer(mock_dependencies):
    """Create EventStreamer instance with mocked dependencies"""
    streamer = MockEventStreamer(
        web3=mock_dependencies['web3'],
        reorg_monitor=mock_dependencies['reorg_monitor'],
        sleep=0.1,
        event_filter=mock_dependencies['event_filter'],
        api_request_counter=mock_dependencies['api_counter']
    )
    
    yield streamer
    
    # Cleanup metrics
    try:
        REGISTRY.unregister(streamer.reorgs_detected_counter)
        REGISTRY.unregister(streamer.api_requests_total_gauge)
    except KeyError:
        pass


def test_metrics_initialization(event_streamer):
    """Test that Prometheus metrics are initialized correctly"""
    # Check metrics exist
    assert event_streamer.reorgs_detected_counter is not None
    assert event_streamer.api_requests_total_gauge is not None
    
    # Check chain ID is set correctly
    assert event_streamer.chain_id == 'ethereum'


def test_reorg_counter_increment(event_streamer):
    """Test that reorg counter increments correctly"""
    # Simulate reorg detection
    event_streamer.total_reorgs = 0
    event_streamer.reorgs_detected_counter.labels(chain_id='ethereum').inc()
    
    # Check counter value
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    assert 'chain_reorganizations_total{chain_id="ethereum"} 1.0' in metrics_output


def test_gauge_updates(event_streamer, mock_dependencies):
    """Test that gauges update correctly"""
    # Mock some buffered blocks
    mock_dependencies['reorg_monitor'].block_map = {'block1': {}, 'block2': {}}
    
    # Update gauges
    event_streamer.api_requests_total_gauge.labels(chain_id='ethereum').set(100)
    
    # Check values
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    assert 'api_requests_total{chain_id="ethereum"} 100.0' in metrics_output


def test_chain_id_mapping(mock_dependencies):
    """Test chain ID mapping works for different networks"""
    test_cases = [
        (1, 'ethereum'),
        (137, 'polygon'),
        (42161, 'arbitrum'),
        (999999, 'chain_999999')  # Unknown chain
    ]
    
    for chain_id, expected_name in test_cases:
        mock_dependencies['web3'].eth.chain_id = chain_id
        
        streamer = MockEventStreamer(
            web3=mock_dependencies['web3'],
            reorg_monitor=mock_dependencies['reorg_monitor'],
            sleep=0.1,
            event_filter=mock_dependencies['event_filter']
        )
        
        assert streamer.chain_id == expected_name
        
        # Cleanup
        try:
            REGISTRY.unregister(streamer.reorgs_detected_counter)
            REGISTRY.unregister(streamer.api_requests_total_gauge)
        except KeyError:
            pass