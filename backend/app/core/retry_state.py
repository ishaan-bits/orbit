"""In-process record of the most recent retry-pending run.

Written by ``POST /documents/retry-pending`` (Render cron or an authenticated
user) and read by ``GET /api/health`` so operators can see when the background
retry last fired. Single-process state: uvicorn runs with one worker.
"""

from datetime import datetime, timezone
from threading import Lock
from typing import Optional

_lock = Lock()
_last_retry_at: Optional[str] = None


def record_retry_run() -> None:
    """Stamp the current UTC time as the last retry-pending run."""
    global _last_retry_at
    with _lock:
        _last_retry_at = datetime.now(timezone.utc).isoformat()


def last_retry_at() -> Optional[str]:
    """ISO-8601 UTC timestamp of the last retry run, or ``None``."""
    with _lock:
        return _last_retry_at


def reset_retry_state() -> None:
    """Clear the record (tests only)."""
    global _last_retry_at
    with _lock:
        _last_retry_at = None
