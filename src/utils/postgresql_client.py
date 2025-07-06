import os
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, generate_event_uuid
from src.models import SwapEvent, MintEvent, BurnEvent

class PostgresClient:
    def __init__(self):
        self._POSTGRES_USER = os.getenv("POSTGRES_USER")
        self._POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        self._POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        self._POSTGRES_DATABASE = os.getenv("POSTGRES_DB")

        self.conn_string = f"postgresql://{self._POSTGRES_USER}:{self._POSTGRES_PASSWORD}@{self._POSTGRES_HOST}/{self._POSTGRES_DATABASE}"
        self.engine = self.create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.init_db()

    def create_engine(self):
        return create_engine(self.conn_string)
    
    def get_session(self):
        return self.Session()
    
    def close(self):
        self.engine.dispose()

    def init_db(self):
        Base.metadata.create_all(self.engine)

    def insert_event(self, event):
        """
        Perform an upsert operation for the given event.
        
        Args:
            event: SQLAlchemy model instance (e.g., SwapEvent, MintEvent, BurnEvent)
            
        Returns:
            The merged event instance
        """
        session = self.get_session()

        if event.id is None:
            event.id = generate_event_uuid(
                block_number=event.block_number,
                tx_hash=event.tx_hash,
                log_index=event.log_index
            )
            event.update_timestamp = datetime.now(timezone.utc)

        try:
            merged_event = session.merge(event)
            session.commit()
            return merged_event
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
        