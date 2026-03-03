from dataclasses import dataclass
from enum import Enum
from typing import Optional, Type


class RetryDecision(str, Enum):
    RETRY = "retry"
    EXTINCT = "extinct"


@dataclass(frozen=True)
class RetryRule:
    decision: RetryDecision
    reason: str
    retryable: bool
    override_backoff_seconds: Optional[int] = None


PERMANENT_EXCEPTIONS: tuple[Type[BaseException], ...] = (
    ValueError,  # like validation
    KeyError,  # lack off payload
)

TRANSIENT_EXCEPTIONS: tuple[Type[BaseException], ...] = (
    TimeoutError,  # simple example
    ConnectionError,  # network
)


def classify_exception(exc: BaseException) -> RetryRule:
    # Permanent
    if isinstance(exc, PERMANENT_EXCEPTIONS):
        return RetryRule(
            decision=RetryDecision.EXTINCT,
            reason=f"permanent:{exc.__class__.__name__}",
            retryable=False,
        )

    # Transient
    if isinstance(exc, TRANSIENT_EXCEPTIONS):
        return RetryRule(
            decision=RetryDecision.RETRY,
            reason=f"transient:{exc.__class__.__name__}",
            retryable=True,
        )

    # Default: calm approach
    # Unknown error: try a few times, then drops EXTINCT (It already has max_retry)
    return RetryRule(
        decision=RetryDecision.RETRY,
        reason=f"unknown:{exc.__class__.__name__}",
        retryable=True,
    )
