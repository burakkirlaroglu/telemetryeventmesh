import random
from datetime import timedelta

def calculate_backoff(retry_count: int) -> timedelta:
    base = 10        # seconds
    max_delay = 900  # 15 min

    # increase exponential
    delay = min(base * (2 ** (retry_count - 1)), max_delay)

    # add random between %0–30
    jitter = int(delay * random.uniform(0.0, 0.3))

    return timedelta(seconds=delay + jitter)