from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, Text, Index, 
    BigInteger, Float, UUID
)
from src.models import Base


class MintEvent(Base):
    """
    SQLAlchemy model for Uniswap V3 mint events.
    
    This model captures all the data from mint events including block information,
    transaction details, pool information, token details, and amounts.
    """
    __tablename__ = 'mint_events'
    __table_args__ = (
        # Unique constraint to prevent duplicates - this is the natural key for blockchain events
        Index('uq_mint_block_tx_log', 'block_number', 'tx_hash', 'log_index', unique=True),
        # Indexes for common query patterns
        Index('idx_mint_block_number', 'block_number'),
        Index('idx_mint_tx_hash', 'tx_hash'),
        Index('idx_mint_pool_address', 'pool_contract_address'),
        Index('idx_mint_timestamp', 'timestamp'),
        Index('idx_mint_event_name', 'event_name'),
        Index('idx_mint_token0_address', 'token0_address'),
        Index('idx_mint_token1_address', 'token1_address'),
        # Composite index for efficient range queries
        Index('idx_mint_block_timestamp', 'block_number', 'timestamp'),
    )

    # Primary key - using auto-incrementing ID for performance
    id = Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False)
    
    # Block and transaction information
    block_number = Column(BigInteger, nullable=False, comment='Block number where the event occurred')
    timestamp = Column(DateTime, nullable=False, comment='Block timestamp when the event occurred')
    tx_hash = Column(String(66), nullable=False, comment='Transaction hash (0x + 64 hex chars)')
    log_index = Column(Integer, nullable=False, comment='Log index within the transaction')
    
    # Pool information
    pool_contract_address = Column(String(42), nullable=False, comment='Pool contract address (0x + 40 hex chars)')
    pool_details = Column(Text, nullable=True, comment='Human readable pool description')
    pool_fee = Column(Float, nullable=True, comment='Pool fee as decimal (e.g., 0.0005 for 0.05%)')
    
    # Position information
    tick_lower = Column(Integer, nullable=False, comment='Lower tick of the position')
    tick_upper = Column(Integer, nullable=False, comment='Upper tick of the position')
    
    # Amount information
    amount = Column(Numeric(78, 0), nullable=False, comment='Total liquidity amount (raw value)')
    amount0 = Column(Numeric(78, 0), nullable=False, comment='Amount of token0')
    amount1 = Column(Numeric(78, 0), nullable=False, comment='Amount of token1')
    
    # Event metadata
    event_name = Column(String(50), nullable=False, comment='Event name (e.g., "Mint")')
    
    # Token0 information
    token0_address = Column(String(42), nullable=False, comment='Token0 contract address')
    token0_symbol = Column(String(20), nullable=True, comment='Token0 symbol')
    token0_name = Column(String(100), nullable=True, comment='Token0 full name')
    token0_decimals = Column(Integer, nullable=True, comment='Token0 decimal places')
    token0_total_supply = Column(Numeric(78, 0), nullable=True, comment='Token0 total supply')
    
    # Token1 information
    token1_address = Column(String(42), nullable=False, comment='Token1 contract address')
    token1_symbol = Column(String(20), nullable=True, comment='Token1 symbol')
    token1_name = Column(String(100), nullable=True, comment='Token1 full name')
    token1_decimals = Column(Integer, nullable=True, comment='Token1 decimal places')
    token1_total_supply = Column(Numeric(78, 0), nullable=True, comment='Token1 total supply')
    
    # Record metadata
    record_timestamp = Column(DateTime, nullable=False, comment='Timestamp when this record was created')
    insert_timestamp = Column(DateTime, nullable=False, comment='Timestamp when this record was inserted into the database', default=datetime.now(timezone.utc))
    update_timestamp = Column(DateTime, nullable=False, comment='Timestamp when this record was last updated', default=datetime.now(timezone.utc))

    def __repr__(self):
        return (
            f"<MintEvent(id={self.id}, "
            f"block_number={self.block_number}, "
            f"tx_hash='{self.tx_hash}', "
            f"pool_address='{self.pool_contract_address}', "
            f"amount={self.amount})>"
        )

    def to_dict(self):
        """Convert the model instance to a dictionary."""
        return {
            'id': self.id,
            'block_number': self.block_number,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
            'pool_contract_address': self.pool_contract_address,
            'tick_lower': self.tick_lower,
            'tick_upper': self.tick_upper,
            'amount': str(self.amount) if self.amount else None,
            'amount0': str(self.amount0) if self.amount0 else None,
            'amount1': str(self.amount1) if self.amount1 else None,
            'event_name': self.event_name,
            'pool_details': self.pool_details,
            'pool_fee': self.pool_fee,
            'token0_address': self.token0_address,
            'token1_address': self.token1_address,
            'token0_symbol': self.token0_symbol,
            'token1_symbol': self.token1_symbol,
            'token0_decimals': self.token0_decimals,
            'token1_decimals': self.token1_decimals,
            'token0_name': self.token0_name,
            'token1_name': self.token1_name,
            'token0_total_supply': str(self.token0_total_supply) if self.token0_total_supply else None,
            'token1_total_supply': str(self.token1_total_supply) if self.token1_total_supply else None,
            'record_timestamp': self.record_timestamp.isoformat() if self.record_timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create a MintEvent instance from a dictionary."""
        # Convert string timestamps to datetime objects
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        if isinstance(data.get('record_timestamp'), str):
            data['record_timestamp'] = datetime.fromisoformat(data['record_timestamp'].replace('Z', '+00:00'))
        
        # Convert numeric strings to Decimal objects
        for field in ['amount', 'amount0', 'amount1', 'token0_total_supply', 'token1_total_supply']:
            if isinstance(data.get(field), str):
                data[field] = Decimal(data[field])
        
        return cls(**data)
