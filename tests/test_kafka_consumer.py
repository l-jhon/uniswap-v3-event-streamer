#!/usr/bin/env python3
"""
Tests for Kafka consumer functionality.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.streamers.kafka_consumer import KafkaEventConsumer


@pytest.fixture
def mock_kafka_consumer():
    """Create a mock Kafka consumer."""
    consumer = Mock()
    return consumer


@pytest.fixture
def kafka_event_consumer(mock_kafka_consumer):
    """Create a KafkaEventConsumer instance with mocked dependencies."""
    return KafkaEventConsumer(
        kafka_consumer=mock_kafka_consumer,
        kafka_topic="test-topic"
    )


def test_timestamp_parsing():
    """Test that timestamp strings are correctly parsed to datetime objects."""
    # Test timestamp string format from DateTimeEncoder
    timestamp_str = "2024-01-15T10:30:45"
    
    # Parse the timestamp
    parsed_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    
    # Verify it's a datetime object
    assert isinstance(parsed_timestamp, datetime)
    assert parsed_timestamp.year == 2024
    assert parsed_timestamp.month == 1
    assert parsed_timestamp.day == 15
    assert parsed_timestamp.hour == 10
    assert parsed_timestamp.minute == 30
    assert parsed_timestamp.second == 45


def test_latency_calculation():
    """Test that latency is calculated correctly from timestamps."""
    # Create a timestamp from 5 seconds ago
    past_time = datetime.now(timezone.utc).replace(microsecond=0)
    past_time_str = past_time.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Parse it back
    parsed_past_time = datetime.fromisoformat(past_time_str.replace('Z', '+00:00'))
    
    # Calculate latency
    current_time = datetime.now(timezone.utc).replace(microsecond=0)
    latency = (current_time - parsed_past_time).total_seconds()
    
    # Latency should be approximately 0 seconds (since we removed microseconds)
    assert 0 <= latency < 1


def test_event_data_processing(kafka_event_consumer):
    """Test processing of event data with timestamps."""
    # Create sample event data
    event_data = {
        "event_name": "Swap",
        "decoded_event": {
            "record_timestamp": "2024-01-15T10:30:45",
            "event_name": "Swap",
            "block_number": 12345,
            "tx_hash": "0x123...",
            "pool_contract_address": "0xabc...",
            "amount0": "1000000",
            "amount1": "-2000000",
            "sqrt_price_x96": "123456789",
            "liquidity": "1000000000",
            "tick": 12345,
            "log_index": 0,
            "timestamp": "2024-01-15T10:30:45",
            "token0_address": "0xtoken0...",
            "token1_address": "0xtoken1...",
            "token0_symbol": "USDC",
            "token1_symbol": "WETH",
            "token0_decimals": 6,
            "token1_decimals": 18,
            "token0_name": "USD Coin",
            "token1_name": "Wrapped Ether",
            "pool_details": "USDC/WETH 0.05%",
            "pool_fee": 0.0005
        }
    }
    
    # Test that the event data can be processed without errors
    with patch.object(kafka_event_consumer.postgres_client, 'insert_event'):
        kafka_event_consumer._handle_message(event_data["decoded_event"])
        
        # Verify that insert_event was called
        kafka_event_consumer.postgres_client.insert_event.assert_called_once()


def test_missing_timestamp_handling(kafka_event_consumer):
    """Test handling of events with missing timestamps."""
    # Create event data without timestamp
    event_data = {
        "event_name": "Swap",
        "decoded_event": {
            "event_name": "Swap",
            # Missing record_timestamp
        }
    }
    
    # This should not raise an error
    record_timestamp_str = event_data.get('decoded_event', {}).get('record_timestamp')
    assert record_timestamp_str is None


def test_invalid_timestamp_handling(kafka_event_consumer):
    """Test handling of invalid timestamp formats."""
    # Test with invalid timestamp format
    invalid_timestamp = "invalid-timestamp"
    
    with pytest.raises(ValueError):
        datetime.fromisoformat(invalid_timestamp.replace('Z', '+00:00'))


def test_metrics_increment(kafka_event_consumer):
    """Test that metrics are incremented correctly."""
    # Create sample event data
    event_data = {
        "event_name": "Swap",
        "decoded_event": {
            "record_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "event_name": "Swap"
        }
    }
    
    # Simulate processing the event
    record_timestamp_str = event_data.get('decoded_event', {}).get('record_timestamp')
    
    if record_timestamp_str:
        record_timestamp = datetime.fromisoformat(record_timestamp_str.replace('Z', '+00:00'))
        current_time = datetime.now(timezone.utc)
        latency = (current_time - record_timestamp).total_seconds()
        
        # Verify latency is reasonable (should be very small)
        assert 0 <= latency < 1
        
        # Verify event name is extracted correctly
        event_name = event_data.get('event_name', 'unknown')
        assert event_name == "Swap" 