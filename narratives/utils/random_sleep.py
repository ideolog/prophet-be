import time
import random

def random_sleep(min_seconds: int, max_seconds: int):
    """
    Sleep for random time between min_seconds and max_seconds.
    Randomness operates on full milliseconds.
    """
    sleep_ms = random.randint(min_seconds * 1000, max_seconds * 1000)
    # Optional micro jitter for extra naturalness
    sleep_ms += random.randint(-50, 50)
    sleep_ms = max(1000, sleep_ms)  # enforce minimum 1 second
    time.sleep(sleep_ms / 1000.0)
