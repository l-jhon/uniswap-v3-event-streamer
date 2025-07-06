from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

def generate_event_uuid(block_number: int, tx_hash: str, log_index: int) -> uuid.UUID:
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    raw = f"{block_number}-{tx_hash.lower()}-{log_index}"
    return uuid.uuid5(namespace, raw)