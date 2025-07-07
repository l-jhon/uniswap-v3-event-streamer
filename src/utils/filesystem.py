import os

def get_checkpoint_path() -> str:
    """Return checkpoint file path (inside/outside Docker)."""
    base_path = "/app/checkpoints" if os.path.exists("/app/checkpoints") else "checkpoints"
    return os.path.join(base_path, f"uni-v3-event-streamer-block-state.csv")
