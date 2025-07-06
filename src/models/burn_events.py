from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, Text, Index, 
    BigInteger, Float
)
from src.models import Base


class BurnEvent(Base):
    """
    SQLAlchemy model for Uniswap V3 burn events.
    
    This model captures all the data from burn events including block information,
    transaction details, pool information, token details, and burn amounts.
    """
    __tablename__ = 'burn_events'
    __table_args__ = (
        # Unique constraint to prevent duplicates
        Index('uq_burn_block_tx_log', 'block_number', 'tx_hash', 'log_index', unique=True),
        # Indexes for common query patterns
        Index('idx_burn_block_number', 'block_number'),
        Index('idx_burn_tx_hash', 'tx_hash'),
        Index('idx_burn_pool_address', 'pool_contract_address'),
        Index('idx_burn_timestamp', 'timestamp'),
        Index('idx_burn_event_name', 'event_name'),
        Index('idx_burn_token0_address', 'token0_address'),
        Index('idx_burn_token1_address', 'token1_address'),
        # Composite index for efficient range queries
        Index('idx_burn_block_timestamp', 'block_number', 'timestamp'),
    )

    # Primary key - using auto-incrementing ID for performance
    id = Column(Integer, primary_key=True, autoincrement=True)
    
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
    amount = Column(Numeric(78, 0), nullable=False, comment='Total liquidity amount burned (raw value)')
    amount0 = Column(Numeric(78, 0), nullable=False, comment='Amount of token0 received from burn')
    amount1 = Column(Numeric(78, 0), nullable=False, comment='Amount of token1 received from burn')
    
    # Event metadata
    event_name = Column(String(50), nullable=False, comment='Event name (e.g., "Burn")')
    
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
            f"<BurnEvent(id={self.id}, "
            f"block_number={self.block_number}, "
            f"tx_hash='{self.tx_hash}', "
            f"pool_address='{self.pool_contract_address}', "
            f"amount={self.amount}, "
            f"amount0={self.amount0}, "
            f"amount1={self.amount1})>"
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
        """Create a BurnEvent instance from a dictionary."""
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

    def get_burn_value_usd(self, token0_price_usd: float = None, token1_price_usd: float = None):
        """
        Calculate the USD value of the burned liquidity.
        
        Args:
            token0_price_usd: Price of token0 in USD
            token1_price_usd: Price of token1 in USD
            
        Returns:
            float: Total USD value of burned liquidity, or None if prices not provided
        """
        if token0_price_usd is None or token1_price_usd is None:
            return None
        
        # Convert amounts to human-readable format using decimals
        token0_amount = float(self.amount0) / (10 ** (self.token0_decimals or 0))
        token1_amount = float(self.amount1) / (10 ** (self.token1_decimals or 0))
        
        # Calculate USD values
        token0_value = token0_amount * token0_price_usd
        token1_value = token1_amount * token1_price_usd
        
        return token0_value + token1_value

    def get_position_range(self):
        """
        Get the price range of the burned position.
        
        Returns:
            tuple: (lower_price, upper_price) in human-readable format
        """
        # This is a simplified calculation - in practice you'd use Uniswap's tick math
        # For now, we'll return the tick values
        return self.tick_lower, self.tick_upper

    def is_partial_burn(self):
        """
        Determine if this is a partial burn (some liquidity remains).
        This would require additional context about the position's total liquidity.
        
        Returns:
            bool: True if likely a partial burn (amount0 or amount1 is 0)
        """
        return self.amount0 == 0 or self.amount1 == 0
