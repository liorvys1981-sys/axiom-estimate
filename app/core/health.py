"""Health check state management."""
import time

# Module-level startup timestamp
_startup_time = time.monotonic()
_ready = False


def mark_ready() -> None:
    """Mark the service as ready to accept traffic."""
    global _ready
    _ready = True


def is_ready() -> bool:
    return _ready


def is_alive() -> bool:
    """Always True while the process is running."""
    return True


def startup_complete() -> bool:
    """True once the app has finished initialising."""
    return _ready


def uptime_seconds() -> float:
    return time.monotonic() - _startup_time
